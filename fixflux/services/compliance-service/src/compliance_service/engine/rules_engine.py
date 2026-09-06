from typing import Any

from compliance_service.rules.base import Rule, Violation
from compliance_service.utils.logger import get_logger

logger = get_logger(__name__)


class RulesEngine:
    """Evaluates a list of rules against an event and returns all violations found."""

    def __init__(self, rules: list[Rule]):
        # Kept unfiltered (not just the initially-enabled ones): rule.enabled can
        # be flipped live after construction (see consumer._refresh_rule_overrides),
        # so it must be re-checked per event rather than baked in once here.
        self.rules = list(rules)
        active = sum(1 for r in self.rules if r.enabled)
        logger.info(
            f"RulesEngine initialised with {active}/{len(self.rules)} active rule(s)"
        )

    def evaluate(self, event: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            try:
                violation = rule.check(event)
                if violation:
                    violations.append(violation)
                    logger.warning(
                        f"VIOLATION [{violation.severity.value}] "
                        f"{violation.rule_name}: {violation.description}"
                    )
            except Exception:
                logger.exception(f"Rule {rule.name} raised an exception")
        return violations
