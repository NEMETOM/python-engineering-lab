"""Execution reports must say PartiallyFilled, with real LeavesQty/CumQty,
whenever a side still has quantity open after a trade."""

from unittest.mock import MagicMock, patch

import pytest

from matching_engine.models import Trade
from matching_engine.producer import Producer


def _make_trade(**overrides):
    defaults = {
        "trade_id": "T1",
        "symbol": "AAPL",
        "buy_order_id": "B1",
        "sell_order_id": "S1",
        "price": 150.0,
        "quantity": 40,
        "buy_client_id": "CLIENT-BUY",
        "sell_client_id": "CLIENT-SELL",
        "buy_order_qty": 40,
        "sell_order_qty": 100,
        "buy_leaves_qty": 0,
        "sell_leaves_qty": 60,
    }
    return Trade(**{**defaults, **overrides})


@pytest.fixture
def reports():
    """Send one trade and return its two exec reports keyed by side."""
    with (
        patch("matching_engine.producer.create_producer"),
        patch("matching_engine.producer.create_exec_report_producer") as create_exec,
    ):
        exec_producer = MagicMock()
        create_exec.return_value = exec_producer
        producer = Producer()

    def _send(trade):
        exec_producer.send.reset_mock()
        producer.send_exec_reports(trade)
        return {c.args[1]["side"]: c.args[1] for c in exec_producer.send.call_args_list}

    return _send


class TestPartialFillReports:
    def test_side_with_quantity_left_is_partially_filled(self, reports):
        r = reports(_make_trade())
        assert (r["SELL"]["ord_status"], r["SELL"]["leaves_qty"]) == ("1", 60)

    def test_fully_filled_side_is_filled(self, reports):
        r = reports(_make_trade())
        assert (r["BUY"]["ord_status"], r["BUY"]["leaves_qty"]) == ("2", 0)

    def test_cum_qty_counts_every_fill_so_far_not_just_this_one(self, reports):
        # Second fill of a 100-lot: 40 earlier + 60 now -> cum 100, leaves 0.
        r = reports(_make_trade(quantity=60, sell_leaves_qty=0))
        assert (r["SELL"]["cum_qty"], r["SELL"]["ord_status"]) == (100, "2")

    def test_cum_qty_after_a_first_partial_fill(self, reports):
        r = reports(_make_trade())
        assert r["SELL"]["cum_qty"] == 40

    def test_last_qty_is_this_trade_only(self, reports):
        r = reports(_make_trade(quantity=60, sell_leaves_qty=0))
        assert r["SELL"]["last_qty"] == 60

    def test_order_without_order_qty_reports_this_fill_as_cum(self, reports):
        # Orders built without order_qty (0) can't know earlier fills.
        r = reports(_make_trade(buy_order_qty=0, quantity=40))
        assert r["BUY"]["cum_qty"] == 40
