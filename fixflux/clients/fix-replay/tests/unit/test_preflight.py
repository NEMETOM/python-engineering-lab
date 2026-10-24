from unittest.mock import MagicMock, patch

from fix_replay.preflight import fetch_metrics, resting_orders

METRICS = """\
# HELP orders_in_book Orders currently resting in the order book
# TYPE orders_in_book gauge
orders_in_book{side="buy",symbol="AAPL"} 2.0
orders_in_book{side="sell",symbol="AAPL"} 1.0
orders_in_book{side="buy",symbol="EURUSD"} 0.0
orders_in_book{symbol="BTCUSD",side="sell"} 4.0
trades_executed_total{symbol="AAPL"} 9.0
"""


class TestRestingOrders:
    def test_sums_both_sides_for_requested_symbols(self):
        assert resting_orders(METRICS, {"AAPL"}) == {"AAPL": 3}

    def test_omits_empty_books_and_unrequested_symbols(self):
        assert resting_orders(METRICS, {"EURUSD", "ETHUSD"}) == {}

    def test_label_order_does_not_matter(self):
        assert resting_orders(METRICS, {"BTCUSD"}) == {"BTCUSD": 4}


class TestFetchMetrics:
    def test_reads_and_decodes_body(self):
        resp = MagicMock()
        resp.read.return_value = b"x 1"
        resp.__enter__.return_value = resp
        with patch("fix_replay.preflight.urllib.request.urlopen", return_value=resp):
            assert fetch_metrics("http://me:8003/metrics") == "x 1"
