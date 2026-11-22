import csv
import io
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from reporting_service.api import main
from reporting_service.feed import FEED_COLUMNS

TRADE = {
    "trade_id": "T1",
    "symbol": "AAPL",
    "asset_class": "equity",
    "price": 175.0,
    "price_currency": "USD",
    "quantity": 100,
    "trading_timestamp": datetime(2026, 11, 22, 11, 59, 59, tzinfo=UTC),
    "reporting_timestamp": datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC),
}

RESTRICTED_MARKERS = ("lei", "client", "capacity", "buyer", "seller", "reason")


@pytest.fixture
def feed():
    fake = MagicMock()
    fake.fetch.return_value = [TRADE]
    main.app.dependency_overrides[main._feed] = lambda: fake
    yield fake
    main.app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(main.app)


class TestHealth:
    def test_health_needs_no_database(self, client):
        assert client.get("/health").json() == {"status": "ok"}


class TestJson:
    def test_returns_trades_with_a_cursor_for_the_next_page(self, client, feed):
        body = client.get("/post-trade").json()
        assert body["count"] == 1
        assert body["trades"][0]["trade_id"] == "T1"
        assert body["next_since"] == "2026-11-22T12:00:00Z"

    def test_empty_page_keeps_the_callers_cursor(self, client, feed):
        feed.fetch.return_value = []
        body = client.get("/post-trade?since=2026-11-22T12:00:00Z").json()
        assert body == {"count": 0, "next_since": "2026-11-22T12:00:00Z", "trades": []}

    def test_no_restricted_field_is_ever_returned(self, client, feed):
        keys = client.get("/post-trade").json()["trades"][0].keys()
        assert not [k for k in keys for m in RESTRICTED_MARKERS if m in k]


class TestQueryParameters:
    @pytest.mark.parametrize("given, passed", [("aapl", "AAPL"), ("EURUSD", "EURUSD")])
    def test_symbol_is_upper_cased(self, client, feed, given, passed):
        client.get(f"/post-trade?symbol={given}")
        assert feed.fetch.call_args.args[0] == passed

    def test_defaults(self, client, feed):
        client.get("/post-trade")
        feed.fetch.assert_called_once_with(None, None, 100)

    def test_since_is_parsed_as_an_aware_datetime(self, client, feed):
        client.get("/post-trade?since=2026-11-22T10:00:00%2B01:00")
        since = feed.fetch.call_args.args[1]
        assert since == datetime(2026, 11, 22, 9, 0, 0, tzinfo=UTC)

    @pytest.mark.parametrize(
        "query",
        [
            "since=2026-11-22T10:00:00",  # no timezone: ambiguous cursor
            "since=yesterday",
            "limit=0",
            "limit=1001",
            "format=xml",
            "symbol=AAPL%27%3B%20DROP",  # quote, semicolon, space
            "symbol=" + "A" * 17,
        ],
    )
    def test_invalid_input_is_rejected_before_the_database(self, client, feed, query):
        assert client.get(f"/post-trade?{query}").status_code == 422
        feed.fetch.assert_not_called()


class TestCsv:
    def test_csv_has_the_feed_columns_as_header(self, client, feed):
        response = client.get("/post-trade?format=csv")
        assert response.headers["content-type"].startswith("text/csv")
        rows = list(csv.DictReader(io.StringIO(response.text)))
        assert tuple(rows[0]) == FEED_COLUMNS
        assert rows[0]["symbol"] == "AAPL"
        assert rows[0]["price"] == "175.0"

    def test_empty_csv_still_has_a_header(self, client, feed):
        feed.fetch.return_value = []
        lines = client.get("/post-trade?format=csv").text.splitlines()
        assert lines == [",".join(FEED_COLUMNS)]

    @pytest.mark.parametrize("symbol", ["=HYPERLINK(1)", "+1", "-1", "@SUM(1)"])
    def test_formula_like_text_is_neutralised(self, client, feed, symbol):
        # Symbols come from injected FIX messages: untrusted text.
        feed.fetch.return_value = [{**TRADE, "symbol": symbol}]
        rows = list(
            csv.DictReader(io.StringIO(client.get("/post-trade?format=csv").text))
        )
        assert rows[0]["symbol"] == "'" + symbol

    def test_numbers_are_not_prefixed(self, client, feed):
        feed.fetch.return_value = [{**TRADE, "price": -1.5}]
        rows = list(
            csv.DictReader(io.StringIO(client.get("/post-trade?format=csv").text))
        )
        assert rows[0]["price"] == "-1.5"


class TestUnavailable:
    def test_database_error_is_a_503_without_details(self, client, feed):
        feed.fetch.side_effect = OperationalError("SELECT", {}, Exception("pw bad"))
        response = client.get("/post-trade")
        assert response.status_code == 503
        assert "pw bad" not in response.text

    def test_unconfigured_feed_is_a_503(self, client):
        main.get_feed.cache_clear()
        with patch.object(main.config, "FEED_DATABASE_URL", None):
            assert client.get("/post-trade").status_code == 503
        main.get_feed.cache_clear()

    def test_configured_feed_connects_with_a_pool_under_the_role_limit(self):
        main.get_feed.cache_clear()
        with (
            patch.object(main.config, "FEED_DATABASE_URL", "postgresql://u:p@h/db"),
            patch.object(main, "create_engine") as create,
        ):
            feed = main.get_feed()
        main.get_feed.cache_clear()
        assert (
            create.call_args.kwargs["pool_size"]
            + create.call_args.kwargs["max_overflow"]
            <= 3
        )
        assert feed.engine is create.return_value
