from sqlalchemy.dialects.postgresql import insert

from reporting_service.models import UNIQUE_TRADE_CONSTRAINT, RegulatoryReportModel
from reporting_service.schemas import RegulatoryTradeReport
from shared.infrastructure.db import SessionLocal


class ReportRepository:

    def save(self, report: RegulatoryTradeReport) -> bool:
        """Insert the report unless one already exists for its trade_id.

        Returns False for a duplicate. Under at-least-once Kafka delivery a
        redelivered trade is expected, not an error, so the conflict is
        absorbed by the database (ON CONFLICT DO NOTHING) rather than raised.
        """
        stmt = (
            insert(RegulatoryReportModel)
            .values(**report.model_dump())
            .on_conflict_do_nothing(constraint=UNIQUE_TRADE_CONSTRAINT)
        )
        session = SessionLocal()
        try:
            result = session.execute(stmt)
            session.commit()
            return result.rowcount == 1
        finally:
            session.close()
