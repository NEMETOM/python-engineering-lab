from datetime import datetime, timezone
from typing import Any

from compliance_service.infrastructure.db import SessionLocal
from compliance_service.models import ClientRiskScore, ComplianceViolation
from compliance_service.rules.base import Violation
from compliance_service.utils.logger import get_logger

logger = get_logger(__name__)


class ViolationRepository:
    def save(self, violation: Violation, risk_contribution: float) -> str:
        session = SessionLocal()
        try:
            record = ComplianceViolation(
                rule_name=violation.rule_name,
                rule_category=violation.rule_category,
                client_id=violation.client_id,
                symbol=violation.symbol,
                order_id=violation.order_id,
                severity=violation.severity.value,
                description=violation.description,
                raw_event=violation.raw_event,
                status="OPEN",
                risk_contribution=risk_contribution,
                detected_at=violation.detected_at,
            )
            session.add(record)
            session.commit()
            violation_id = str(record.id)
            logger.info(
                f"Violation saved id={violation_id} rule={violation.rule_name} "
                f"severity={violation.severity.value}"
            )
            return violation_id
        finally:
            session.close()

    def upsert_risk_score(
        self,
        client_id: str,
        score_delta: float,
        is_high_risk: bool,
    ) -> None:
        session = SessionLocal()
        try:
            record = session.get(ClientRiskScore, client_id)
            if record:
                record.risk_score = float(record.risk_score) + score_delta  # type: ignore[assignment]
                record.violation_count += 1  # type: ignore[assignment]
                record.is_high_risk = is_high_risk  # type: ignore[assignment]
                record.last_violation_at = datetime.now(timezone.utc)  # type: ignore[assignment]
                record.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            else:
                record = ClientRiskScore(
                    client_id=client_id,
                    risk_score=score_delta,
                    violation_count=1,
                    is_high_risk=is_high_risk,
                    last_violation_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(record)
            session.commit()
        finally:
            session.close()

    def list_violations(
        self,
        client_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        rule_name: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            q = session.query(ComplianceViolation)
            if client_id:
                q = q.filter(ComplianceViolation.client_id == client_id)
            if severity:
                q = q.filter(ComplianceViolation.severity == severity.upper())
            if status:
                q = q.filter(ComplianceViolation.status == status.upper())
            if rule_name:
                q = q.filter(ComplianceViolation.rule_name == rule_name)
            q = q.order_by(ComplianceViolation.detected_at.desc()).limit(limit)
            return [self._to_dict(v) for v in q.all()]
        finally:
            session.close()

    def get_by_id(self, violation_id: str) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            record = session.get(ComplianceViolation, violation_id)
            return self._to_dict(record) if record else None
        finally:
            session.close()

    def update_status(
        self,
        violation_id: str,
        status: str,
        reviewed_by: str | None,
    ) -> bool:
        session = SessionLocal()
        try:
            record = session.get(ComplianceViolation, violation_id)
            if not record:
                return False
            record.status = status.upper()  # type: ignore[assignment]
            record.reviewed_by = reviewed_by  # type: ignore[assignment]
            record.reviewed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            session.commit()
            return True
        finally:
            session.close()

    def list_risk_scores(self, limit: int = 100) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            records = (
                session.query(ClientRiskScore)
                .order_by(ClientRiskScore.risk_score.desc())
                .limit(limit)
                .all()
            )
            return [self._risk_to_dict(r) for r in records]
        finally:
            session.close()

    def get_risk_score(self, client_id: str) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            record = session.get(ClientRiskScore, client_id)
            return self._risk_to_dict(record) if record else None
        finally:
            session.close()

    def _to_dict(self, v: ComplianceViolation) -> dict[str, Any]:
        return {
            "id": str(v.id),
            "rule_name": v.rule_name,
            "rule_category": v.rule_category,
            "client_id": v.client_id,
            "symbol": v.symbol,
            "order_id": v.order_id,
            "severity": v.severity,
            "description": v.description,
            "status": v.status,
            "risk_contribution": v.risk_contribution,
            "detected_at": v.detected_at.isoformat() if v.detected_at else None,
            "reviewed_at": v.reviewed_at.isoformat() if v.reviewed_at else None,
            "reviewed_by": v.reviewed_by,
        }

    def _risk_to_dict(self, r: ClientRiskScore) -> dict[str, Any]:
        return {
            "client_id": r.client_id,
            "risk_score": r.risk_score,
            "violation_count": r.violation_count,
            "last_violation_at": (
                r.last_violation_at.isoformat() if r.last_violation_at else None
            ),
            "is_high_risk": r.is_high_risk,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
