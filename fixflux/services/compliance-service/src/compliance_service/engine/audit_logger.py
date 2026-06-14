import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from compliance_service.infrastructure.db import SessionLocal
from compliance_service.models import ComplianceAuditTrail
from compliance_service.utils.logger import get_logger

logger = get_logger(__name__)


def _checksum(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class AuditLogger:
    """Appends tamper-evident records to the compliance audit trail."""

    def log(
        self,
        event_type: str,
        action: str,
        payload: dict[str, Any],
        client_id: str | None = None,
        entity_id: str | None = None,
        entity_type: str | None = None,
    ) -> None:
        checksum = _checksum(payload)
        entry = ComplianceAuditTrail(
            event_type=event_type,
            client_id=client_id,
            entity_id=entity_id,
            entity_type=entity_type,
            action=action,
            payload=payload,
            checksum=checksum,
            recorded_at=datetime.now(timezone.utc),
        )
        session = SessionLocal()
        try:
            session.add(entry)
            session.commit()
        except Exception as exc:
            logger.error(f"Failed to write audit trail entry: {exc}", exc_info=True)
        finally:
            session.close()
