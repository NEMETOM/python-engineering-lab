"""Partial fills: the matching engine keeps a partly filled order resting, so
risk must keep counting it as open and move the position by the filled part
only. Previously the first trade closed the whole order at full quantity."""

from risk_service.consumer import handle_trade
from risk_service.position_store import PositionStore


def _make_store_with_order(side="BUY", quantity=100):
    store = PositionStore()
    store.record_open_order("O1", "C1", "AAPL", side, quantity)
    return store


def _make_trade(**overrides):
    defaults = {
        "trade_id": "T1",
        "symbol": "AAPL",
        "buy_order_id": "O1",
        "sell_order_id": "O-OTHER",
        "price": 100.0,
        "quantity": 40,
    }
    return {**defaults, **overrides}


class TestPartialFill:
    def test_partly_filled_order_stays_open(self):
        store = _make_store_with_order()
        store.fill_order("O1", 40)
        assert store.get_open_order_count("C1") == 1

    def test_position_moves_by_the_filled_quantity_only(self):
        store = _make_store_with_order()
        store.fill_order("O1", 40)
        assert store.get_net_position("C1", "AAPL") == 40

    def test_sell_partial_fill_reduces_position_by_filled_part(self):
        store = _make_store_with_order(side="SELL")
        store.fill_order("O1", 30)
        assert store.get_net_position("C1", "AAPL") == -30

    def test_order_closes_once_the_remainder_fills(self):
        store = _make_store_with_order()
        store.fill_order("O1", 40)
        store.fill_order("O1", 60)
        assert store.get_open_order_count("C1") == 0
        assert store.get_net_position("C1", "AAPL") == 100

    def test_overfill_is_capped_at_the_open_quantity(self):
        store = _make_store_with_order(quantity=50)
        store.fill_order("O1", 80)
        assert store.get_net_position("C1", "AAPL") == 50
        assert store.get_open_order_count("C1") == 0

    def test_no_quantity_still_fills_everything_open(self):
        store = _make_store_with_order()
        store.fill_order("O1", 40)
        store.fill_order("O1")
        assert store.get_net_position("C1", "AAPL") == 100
        assert store.get_open_order_count("C1") == 0


class TestHandleTradePartialFill:
    def test_trade_quantity_is_applied_not_the_whole_order(self):
        store = _make_store_with_order(quantity=100)
        handle_trade(_make_trade(quantity=40), store, {})
        assert store.get_net_position("C1", "AAPL") == 40
        assert store.get_open_order_count("C1") == 1
