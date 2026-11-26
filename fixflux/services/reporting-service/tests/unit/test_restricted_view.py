from unittest.mock import MagicMock

import pytest

from reporting_service.models import RegulatoryReportModel
from reporting_service.public_view import PUBLIC_COLUMNS, VIEW_NAME
from reporting_service.restricted_view import (
    REGULATOR_ROLE,
    RESTRICTED_COLUMNS,
    RESTRICTED_VIEW_NAME,
    RESTRICTED_VIEW_SQL,
    ensure_restricted_view,
)


def _make_engine(role_exists=False):
    """Engine whose begin() yields a connection recording every statement."""
    conn = MagicMock()
    conn.execute.return_value.scalar.return_value = 1 if role_exists else None
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    return engine, conn


def _executed_sql(conn) -> list[str]:
    return [str(c.args[0]) for c in conn.execute.call_args_list]


class TestRestrictedColumns:
    @pytest.mark.parametrize(
        "column",
        [
            "buyer_lei",
            "seller_lei",
            "buyer_trading_capacity",
            "seller_trading_capacity",
            "cfi_code",
            "status_reason",
        ],
    )
    def test_regulator_view_carries_the_transaction_reporting_fields(self, column):
        assert column in RESTRICTED_COLUMNS

    @pytest.mark.parametrize("column", ["buyer_client_id", "seller_client_id"])
    def test_internal_client_ids_are_not_columns(self, column):
        # A regulator identifies parties by LEI, not by our internal IDs.
        assert column not in RESTRICTED_COLUMNS

    def test_every_restricted_column_exists_on_the_table(self):
        columns = {c.name for c in RegulatoryReportModel.__table__.columns}
        assert set(RESTRICTED_COLUMNS) <= columns

    def test_restricted_fields_never_leak_into_the_public_view(self):
        restricted_only = set(RESTRICTED_COLUMNS) - set(PUBLIC_COLUMNS)
        assert {"buyer_lei", "seller_lei"} <= restricted_only
        assert not restricted_only & set(PUBLIC_COLUMNS)

    def test_view_reads_the_base_table_unfiltered(self):
        assert RESTRICTED_VIEW_SQL.startswith(
            f"CREATE OR REPLACE VIEW {RESTRICTED_VIEW_NAME} AS SELECT "
        )
        assert RESTRICTED_VIEW_SQL.endswith(" FROM regulatory_reports")


class TestEnsureRestrictedView:
    def test_without_password_only_the_view_is_created(self):
        engine, conn = _make_engine()
        assert ensure_restricted_view(engine, None) is False
        assert _executed_sql(conn) == [RESTRICTED_VIEW_SQL]

    def test_empty_password_is_skipped_not_defaulted(self):
        engine, conn = _make_engine()
        assert ensure_restricted_view(engine, "") is False
        assert not [s for s in _executed_sql(conn) if REGULATOR_ROLE in s]

    def test_regulator_role_is_granted_the_restricted_view_only(self):
        engine, conn = _make_engine(role_exists=False)
        assert ensure_restricted_view(engine, "s3cret") is True
        grants = [s for s in _executed_sql(conn) if s.startswith("GRANT")]
        # Not the base table, and not the public view either.
        assert grants == [f"GRANT SELECT ON {RESTRICTED_VIEW_NAME} TO {REGULATOR_ROLE}"]
        assert not [g for g in grants if VIEW_NAME in g]

    @pytest.mark.parametrize(
        "setting",
        [
            "default_transaction_read_only = on",
            "statement_timeout = '5s'",
            "idle_in_transaction_session_timeout = '30s'",
        ],
    )
    def test_regulator_role_gets_the_same_hardening_as_public_readers(self, setting):
        engine, conn = _make_engine()
        ensure_restricted_view(engine, "pw")
        assert f"ALTER ROLE {REGULATOR_ROLE} SET {setting}" in _executed_sql(conn)

    def test_existing_role_gets_its_password_rotated(self):
        engine, conn = _make_engine(role_exists=True)
        ensure_restricted_view(engine, "rotated")
        assert (
            f"ALTER ROLE {REGULATOR_ROLE} LOGIN CONNECTION LIMIT 3 PASSWORD 'rotated'"
            in _executed_sql(conn)
        )

    def test_runs_in_one_transaction(self):
        engine, _ = _make_engine()
        ensure_restricted_view(engine, "pw")
        engine.begin.assert_called_once()
