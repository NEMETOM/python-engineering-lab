from unittest.mock import MagicMock

import pytest

from reporting_service.models import RegulatoryReportModel
from reporting_service.public_view import (
    PUBLIC_COLUMNS,
    READER_ROLE,
    VIEW_NAME,
    VIEW_SQL,
    ensure_public_view,
)

RESTRICTED_MARKERS = ("lei", "client", "capacity", "buyer", "seller")


def _make_engine(role_exists=False):
    """Engine whose begin() yields a connection recording every statement."""
    conn = MagicMock()
    conn.execute.return_value.scalar.return_value = 1 if role_exists else None
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    return engine, conn


def _executed_sql(conn) -> list[str]:
    return [str(c.args[0]) for c in conn.execute.call_args_list]


class TestPublicColumns:
    @pytest.mark.parametrize("marker", RESTRICTED_MARKERS)
    def test_no_counterparty_identifying_column_is_public(self, marker):
        # RTS 1 publication must not identify counterparties.
        assert not [c for c in PUBLIC_COLUMNS if marker in c]

    def test_every_public_column_exists_on_the_table(self):
        columns = {c.name for c in RegulatoryReportModel.__table__.columns}
        assert set(PUBLIC_COLUMNS) <= columns

    def test_incomplete_reasons_are_redacted(self):
        # INCOMPLETE reasons name the client ("no LEI for buyer VOL_B0001").
        assert "WHEN status = 'INCOMPLETE'" in VIEW_SQL
        assert "details restricted" in VIEW_SQL
        assert "status_reason," not in VIEW_SQL  # only exposed via the CASE


class TestEnsurePublicView:
    def test_without_password_only_the_view_is_created(self):
        engine, conn = _make_engine()
        assert ensure_public_view(engine, None) is False
        assert _executed_sql(conn) == [VIEW_SQL]

    def test_new_role_is_created_and_granted_the_view_only(self):
        engine, conn = _make_engine(role_exists=False)
        assert ensure_public_view(engine, "s3cret") is True
        sql = _executed_sql(conn)
        assert sql[0] == VIEW_SQL
        assert (
            f"CREATE ROLE {READER_ROLE} LOGIN CONNECTION LIMIT 3 PASSWORD 's3cret'"
            in sql
        )
        assert sql[-1] == f"GRANT SELECT ON {VIEW_NAME} TO {READER_ROLE}"
        assert not [s for s in sql if "regulatory_reports " in s and "GRANT" in s]

    def test_existing_role_gets_its_password_rotated(self):
        engine, conn = _make_engine(role_exists=True)
        ensure_public_view(engine, "rotated")
        assert (
            f"ALTER ROLE {READER_ROLE} LOGIN CONNECTION LIMIT 3 PASSWORD 'rotated'"
            in _executed_sql(conn)
        )

    @pytest.mark.parametrize("role_exists", [False, True])
    @pytest.mark.parametrize(
        "setting",
        [
            "default_transaction_read_only = on",  # no writes, even if over-granted
            "statement_timeout = '5s'",  # no CPU-starving Explore queries
            "idle_in_transaction_session_timeout = '30s'",  # no held locks
        ],
    )
    def test_stolen_password_is_limited_by_role_settings(self, role_exists, setting):
        # Applied on every start, so an existing role is hardened too.
        engine, conn = _make_engine(role_exists=role_exists)
        ensure_public_view(engine, "pw")
        assert f"ALTER ROLE {READER_ROLE} SET {setting}" in _executed_sql(conn)

    def test_settings_are_not_applied_without_a_password(self):
        engine, conn = _make_engine()
        ensure_public_view(engine, None)
        assert not [s for s in _executed_sql(conn) if " SET " in s]

    def test_quote_in_password_cannot_break_out_of_the_literal(self):
        engine, conn = _make_engine()
        ensure_public_view(engine, "pa'ss; DROP TABLE x")
        assert "PASSWORD 'pa''ss; DROP TABLE x'" in " ".join(_executed_sql(conn))

    def test_runs_in_one_transaction(self):
        engine, _ = _make_engine()
        ensure_public_view(engine, "s3cret")
        engine.begin.assert_called_once()
