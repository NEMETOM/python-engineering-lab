import os
import threading
import time
from typing import Any

from compliance_service.config import load_policies
from compliance_service.engine.audit_logger import AuditLogger
from compliance_service.engine.risk_scorer import RiskScorer
from compliance_service.engine.rules_engine import RulesEngine
from compliance_service.infrastructure.db import Base, engine
from compliance_service.repository.rule_override_repository import (
    RuleOverrideRepository,
)
from compliance_service.repository.violation_repository import ViolationRepository
from compliance_service.rules.base import Rule
from compliance_service.rules.catalog import rule_ids_by_category
from compliance_service.rules.loader import (
    build_compliance_rules,
    build_surveillance_rules,
)
from compliance_service.utils.logger import configure_logging, get_logger
from shared.infrastructure.kafka_client import create_consumer
from shared.observability.metrics import violations_detected

configure_logging()
logger = get_logger(__name__)

_OVERRIDE_REFRESH_SECONDS = int(
    os.getenv("COMPLIANCE_RULE_OVERRIDE_REFRESH_SECONDS", "5")
)


def _build_rule_registry(
    compliance_rules: list[Rule], surveillance_rules: list[Rule]
) -> dict[str, Rule]:
    """Maps catalog rule_ids to the actual live Rule instances RulesEngine holds,
    so overrides mutate the objects that are really evaluated - not a copy."""
    compliance_ids = rule_ids_by_category("compliance")
    surveillance_ids = rule_ids_by_category("surveillance")
    if len(compliance_ids) != len(compliance_rules) or len(surveillance_ids) != len(
        surveillance_rules
    ):
        raise RuntimeError(
            "rules/catalog.py has drifted from rules/loader.py's rule "
            f"construction order: compliance {len(compliance_ids)} ids vs "
            f"{len(compliance_rules)} rules, surveillance {len(surveillance_ids)} "
            f"ids vs {len(surveillance_rules)} rules"
        )
    return dict(zip(compliance_ids, compliance_rules)) | dict(
        zip(surveillance_ids, surveillance_rules)
    )


def _refresh_rule_overrides(rule_registry: dict[str, Rule]) -> None:
    """Background loop: polls compliance_rule_overrides and applies them to the
    live rule instances. A plain bool attribute set is atomic under the GIL, so
    no lock is needed even though raw_orders/validated_orders consumer threads
    read rule.enabled concurrently."""
    repo = RuleOverrideRepository()
    while True:
        time.sleep(_OVERRIDE_REFRESH_SECONDS)
        try:
            overrides = repo.get_all()
        except Exception:
            logger.exception("Failed to refresh compliance rule overrides")
            continue
        for rule_id, enabled in overrides.items():
            rule = rule_registry.get(rule_id)
            if rule is None:
                continue
            if rule.enabled != enabled:
                logger.info(
                    f"rule override applied | rule_id={rule_id} enabled={enabled}"
                )
            rule.enabled = enabled


def _process_event(
    event: dict[str, Any],
    rules_engine: RulesEngine,
    risk_scorer: RiskScorer,
    repo: ViolationRepository,
    auditor: AuditLogger,
    event_type: str,
) -> None:
    client_id = event.get("client_id") or event.get("49") or "UNKNOWN"

    auditor.log(
        event_type="order_received",
        action=f"{event_type}_consumed",
        payload=event,
        client_id=client_id,
    )

    violations = rules_engine.evaluate(event)
    rule_names = [v.rule_name for v in violations]
    status = "VIOLATIONS_DETECTED" if violations else "COMPLIANT"
    logger.info(
        f"compliance_decision | client={client_id}"
        f" symbol={event.get('symbol')} qty={event.get('quantity')} price={event.get('price')}"
        f" status={status} violations={len(violations)} rules={rule_names}"
    )
    for violation in violations:
        violations_detected.labels(
            rule=violation.rule_name, severity=violation.severity.value
        ).inc()
        score = risk_scorer.score(violation)
        violation_id = repo.save(violation, risk_contribution=score)

        if violation.client_id:
            current = repo.get_risk_score(violation.client_id)
            current_total = float(current["risk_score"]) if current else 0.0
            new_total = current_total + score
            repo.upsert_risk_score(
                client_id=violation.client_id,
                score_delta=score,
                is_high_risk=risk_scorer.is_high_risk(new_total),
            )

        auditor.log(
            event_type="violation_detected",
            action=f"rule_{violation.rule_name}_triggered",
            payload={
                "violation_id": violation_id,
                "rule_name": violation.rule_name,
                "severity": violation.severity.value,
                "description": violation.description,
                "risk_contribution": score,
            },
            client_id=violation.client_id,
            entity_id=violation_id,
            entity_type="compliance_violation",
        )


def _run_consumer(topic: str, group_id: str, rules_engine: RulesEngine) -> None:
    policies = load_policies()
    risk_scorer = RiskScorer(policies.get("risk_scoring", {}))
    repo = ViolationRepository()
    auditor = AuditLogger()

    logger.info(f"Starting compliance consumer: topic={topic} group={group_id}")
    consumer = create_consumer(topic, group_id)
    for msg in consumer:
        try:
            _process_event(
                event=msg.value,
                rules_engine=rules_engine,
                risk_scorer=risk_scorer,
                repo=repo,
                auditor=auditor,
                event_type=topic,
            )
        except Exception:
            logger.exception(
                f"Failed to process message from {topic} | raw={msg.value}",
            )


def run() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Compliance database tables ensured")

    policies = load_policies()
    compliance_rules = build_compliance_rules(policies)
    surveillance_rules = build_surveillance_rules(policies)
    compliance_engine = RulesEngine(compliance_rules)
    surveillance_engine = RulesEngine(surveillance_rules)
    rule_registry = _build_rule_registry(compliance_rules, surveillance_rules)

    raw_orders_thread = threading.Thread(
        target=_run_consumer,
        args=("raw_orders", "compliance-raw", compliance_engine),
        daemon=True,
        name="compliance-raw-orders",
    )
    validated_orders_thread = threading.Thread(
        target=_run_consumer,
        args=("validated_orders", "compliance-validated", surveillance_engine),
        daemon=True,
        name="compliance-validated-orders",
    )
    overrides_thread = threading.Thread(
        target=_refresh_rule_overrides,
        args=(rule_registry,),
        daemon=True,
        name="compliance-rule-overrides",
    )

    raw_orders_thread.start()
    validated_orders_thread.start()
    overrides_thread.start()
    logger.info(
        "Compliance consumer threads started - "
        "raw_orders + validated_orders + rule-overrides"
    )

    raw_orders_thread.join()
    validated_orders_thread.join()


if __name__ == "__main__":
    run()
