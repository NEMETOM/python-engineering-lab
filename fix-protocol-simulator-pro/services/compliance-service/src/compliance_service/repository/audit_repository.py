from typing import Any

from compliance_service.infrastructure.db import SessionLocal
from compliance_service.models import ComplianceAuditTrail


class AuditRepository:
    def list_entries(
        self,
        client_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            q = session.query(ComplianceAuditTrail)
            if client_id:
                q = q.filter(ComplianceAuditTrail.client_id == client_id)
            if event_type:
                q = q.filter(ComplianceAuditTrail.event_type == event_type)
            q = q.order_by(ComplianceAuditTrail.recorded_at.desc()).limit(limit)
            return [self._to_dict(e) for e in q.all()]
        finally:
            session.close()

    def _to_dict(self, e: ComplianceAuditTrail) -> dict[str, Any]:
        return {
            "id": e.id,
            "event_type": e.event_type,
            "client_id": e.client_id,
            "entity_id": e.entity_id,
            "entity_type": e.entity_type,
            "action": e.action,
            "payload": e.payload,
            "checksum": e.checksum,
            "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
        }
