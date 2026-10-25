from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from reporting_service.models import RegulatoryReportModel
from reporting_service.repository import ReportRepository
from reporting_service.schemas import RegulatoryTradeReport


def _make_report(**overrides):
    defaults = {
        "trade_id": "T1",
        "symbol": "EURUSD",
        "price": 1.085,
        "price_currency": "USD",
        "quantity": 1000,
        "trading_timestamp": datetime(2026, 10, 25, 12, 0, tzinfo=UTC),
        "reporting_timestamp": datetime(2026, 10, 25, 12, 0, 1, tzinfo=UTC),
        "buyer_client_id": "B",
        "seller_client_id": "S",
        "buyer_lei": None,
        "seller_lei": None,
        "buyer_trading_capacity": None,
        "seller_trading_capacity": None,
        "cfi_code": None,
        "asset_class": "FX_SPOT",
        "status": "NOT_REPORTABLE",
        "status_reason": "out of scope",
        "publication_latency_ms": 1000,
        "deadline_breached": False,
    }
    return RegulatoryTradeReport(**{**defaults, **overrides})


def _make_session(rowcount=1):
    session = MagicMock()
    session.execute.return_value.rowcount = rowcount
    return session


def _sql(session) -> str:
    stmt = session.execute.call_args.args[0]
    return str(stmt.compile(dialect=postgresql.dialect()))


class TestSave:
    def test_new_trade_is_inserted_and_committed(self):
        session = _make_session(rowcount=1)
        with patch("reporting_service.repository.SessionLocal", return_value=session):
            assert ReportRepository().save(_make_report()) is True
        session.commit.assert_called_once()
        session.close.assert_called_once()

    def test_duplicate_trade_is_absorbed_not_raised(self):
        # Kafka redelivery: the DB's ON CONFLICT DO NOTHING inserts 0 rows.
        session = _make_session(rowcount=0)
        with patch("reporting_service.repository.SessionLocal", return_value=session):
            assert ReportRepository().save(_make_report()) is False

    def test_insert_uses_on_conflict_on_the_trade_id_constraint(self):
        session = _make_session()
        with patch("reporting_service.repository.SessionLocal", return_value=session):
            ReportRepository().save(_make_report())
        sql = _sql(session)
        assert "INSERT INTO regulatory_reports" in sql
        assert (
            "ON CONFLICT ON CONSTRAINT uq_regulatory_reports_trade_id DO NOTHING" in sql
        )

    def test_every_report_field_maps_to_a_column(self):
        columns = {c.name for c in RegulatoryReportModel.__table__.columns}
        assert set(RegulatoryTradeReport.model_fields) <= columns

    def test_session_closed_even_if_commit_raises(self):
        session = _make_session()
        session.commit.side_effect = RuntimeError("DB error")
        with (
            patch("reporting_service.repository.SessionLocal", return_value=session),
            pytest.raises(RuntimeError),
        ):
            ReportRepository().save(_make_report())
        session.close.assert_called_once()


class TestModel:
    def test_trade_id_has_a_named_unique_constraint(self):
        constraints = {
            c.name: [col.name for col in c.columns]
            for c in RegulatoryReportModel.__table__.constraints
            if c.name
        }
        assert constraints["uq_regulatory_reports_trade_id"] == ["trade_id"]
