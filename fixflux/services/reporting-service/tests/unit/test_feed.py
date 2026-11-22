from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from reporting_service.feed import FEED_COLUMNS, PostTradeFeed, build_query
from reporting_service.public_view import PUBLIC_COLUMNS, VIEW_NAME

NOW = datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC)
SINCE = datetime(2026, 11, 22, 11, 0, 0, tzinfo=UTC)


def _row(trade_id: str) -> MagicMock:
    return MagicMock(_mapping={"trade_id": trade_id})


def _make_feed(rows=(), delay_seconds=0):
    conn = MagicMock()
    conn.execute.return_value = list(rows)
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    return PostTradeFeed(engine, delay_seconds, clock=lambda: NOW), conn


def _executed(conn) -> tuple[str, dict]:
    sql, params = conn.execute.call_args.args
    return str(sql), params


class TestFeedColumns:
    def test_feed_reads_only_columns_of_the_public_view(self):
        assert set(FEED_COLUMNS) <= set(PUBLIC_COLUMNS)

    def test_feed_does_not_expose_the_status_reason(self):
        # INCOMPLETE reasons describe our reference data, not the trade.
        assert "reason" not in FEED_COLUMNS


class TestBuildQuery:
    def test_reads_the_public_view_never_the_table(self):
        sql = build_query(None, None, 10)
        assert f"FROM {VIEW_NAME} " in sql
        assert "FROM regulatory_reports " not in sql

    @pytest.mark.parametrize("symbol", [None, "AAPL"])
    @pytest.mark.parametrize("since", [None, SINCE])
    def test_only_reportable_trades_up_to_the_cutoff_are_published(self, symbol, since):
        sql = build_query(symbol, since, 10)
        assert "status = 'REPORTABLE'" in sql
        assert "reporting_timestamp <= :cutoff" in sql

    @pytest.mark.parametrize(
        "symbol, since, present, absent",
        [
            (None, None, [], ["symbol = :symbol", ":since"]),
            ("AAPL", None, ["symbol = :symbol"], [":since"]),
            (None, SINCE, ["reporting_timestamp > :since"], ["symbol = :symbol"]),
        ],
    )
    def test_filters_appear_only_when_requested(self, symbol, since, present, absent):
        sql = build_query(symbol, since, 10)
        assert all(p in sql for p in present)
        assert not [a for a in absent if a in sql]

    @pytest.mark.parametrize("since, order", [(None, "DESC"), (SINCE, "ASC")])
    def test_latest_page_without_since_next_page_with_it(self, since, order):
        sql = build_query(None, since, 10)
        assert (
            f"ORDER BY reporting_timestamp {order}, trade_id {order} LIMIT :limit"
            in sql
        )

    def test_user_input_is_bound_never_interpolated(self):
        sql = build_query("X'; DROP TABLE trades; --", SINCE, 10)
        assert "DROP" not in sql


class TestFetch:
    @pytest.mark.parametrize("delay_seconds", [0, 900])
    def test_cutoff_holds_back_trades_newer_than_the_delay(self, delay_seconds):
        feed, conn = _make_feed(delay_seconds=delay_seconds)
        feed.fetch(None, None, 10)
        _, params = _executed(conn)
        assert params["cutoff"] == NOW - timedelta(seconds=delay_seconds)

    def test_parameters_are_passed_as_binds(self):
        feed, conn = _make_feed()
        feed.fetch("AAPL", SINCE, 50)
        _, params = _executed(conn)
        assert params == {"cutoff": NOW, "limit": 50, "symbol": "AAPL", "since": SINCE}

    def test_unused_filters_are_not_bound(self):
        feed, conn = _make_feed()
        feed.fetch(None, None, 50)
        _, params = _executed(conn)
        assert set(params) == {"cutoff", "limit"}

    @pytest.mark.parametrize(
        "since, db_order, expected",
        [
            # Latest page is read newest first, returned oldest first.
            (None, ["T3", "T2", "T1"], ["T1", "T2", "T3"]),
            # Next page is already read oldest first.
            (SINCE, ["T1", "T2", "T3"], ["T1", "T2", "T3"]),
        ],
    )
    def test_rows_always_come_back_oldest_first(self, since, db_order, expected):
        feed, _ = _make_feed(rows=[_row(t) for t in db_order])
        trades = feed.fetch(None, since, 10)
        assert [t["trade_id"] for t in trades] == expected
