from compliance_service.infrastructure.db import SessionLocal
from compliance_service.models import RuleOverride
from compliance_service.utils.logger import get_logger

logger = get_logger(__name__)


class RuleOverrideRepository:
    def get_all(self) -> dict[str, bool]:
        session = SessionLocal()
        try:
            rows = session.query(RuleOverride).all()
            return {row.rule_id: row.enabled for row in rows}  # type: ignore[misc]
        finally:
            session.close()

    def upsert(self, rule_id: str, enabled: bool) -> RuleOverride:
        session = SessionLocal()
        try:
            record = session.get(RuleOverride, rule_id)
            if record:
                record.enabled = enabled  # type: ignore[assignment]
            else:
                record = RuleOverride(rule_id=rule_id, enabled=enabled)
                session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(f"rule override upserted | rule_id={rule_id} enabled={enabled}")
            return record
        finally:
            session.close()
