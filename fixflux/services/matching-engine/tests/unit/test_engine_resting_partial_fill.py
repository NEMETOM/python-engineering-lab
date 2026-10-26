"""Regression: a partly filled RESTING order must keep its remainder.

The engine used to pop the best resting order before matching, so whatever
the incoming order didn't take silently vanished from the book.
"""

from matching_engine.models import Order


def _make_order(order_id, side, price=100.0, quantity=100, **overrides):
    return Order(order_id, side, price, quantity, order_qty=quantity, **overrides)


class TestRestingRemainderStaysInBook:
    def test_partly_lifted_ask_keeps_its_remainder(self, engine):
        engine.books[""].add_order(_make_order("S1", "SELL", quantity=100))
        engine.process(_make_order("B1", "BUY", quantity=40))
        assert [(o.order_id, o.quantity) for o in engine.books[""].sells] == [
            ("S1", 60)
        ]

    def test_partly_hit_bid_keeps_its_remainder(self, engine):
        engine.books[""].add_order(_make_order("B1", "BUY", quantity=100))
        engine.process(_make_order("S1", "SELL", quantity=30))
        assert [(o.order_id, o.quantity) for o in engine.books[""].buys] == [("B1", 70)]

    def test_remainder_keeps_time_priority_at_its_price(self, engine):
        # The partly filled order was first at 100.0, so it must still be
        # first - ahead of a later order at the same price.
        engine.books[""].add_order(_make_order("S1", "SELL", quantity=100))
        engine.books[""].add_order(_make_order("S2", "SELL", quantity=50))
        engine.process(_make_order("B1", "BUY", quantity=40))
        engine.process(_make_order("B2", "BUY", quantity=10))
        assert [(o.order_id, o.quantity) for o in engine.books[""].sells] == [
            ("S1", 50),
            ("S2", 50),
        ]

    def test_sweep_ends_with_a_partial_fill_on_the_last_level(self, engine):
        engine.books[""].add_order(_make_order("S1", "SELL", price=99.0, quantity=30))
        engine.books[""].add_order(_make_order("S2", "SELL", price=100.0, quantity=50))
        trades = engine.process(_make_order("B1", "BUY", quantity=60))
        assert [(t.sell_order_id, t.quantity) for t in trades] == [
            ("S1", 30),
            ("S2", 30),
        ]
        assert [(o.order_id, o.quantity) for o in engine.books[""].sells] == [
            ("S2", 20)
        ]

    def test_remainder_can_be_filled_later(self, engine):
        engine.books[""].add_order(_make_order("S1", "SELL", quantity=100))
        engine.process(_make_order("B1", "BUY", quantity=40))
        trades = engine.process(_make_order("B2", "BUY", quantity=60))
        assert [(t.sell_order_id, t.quantity) for t in trades] == [("S1", 60)]
        assert engine.books[""].sells == []


class TestTradeLeavesQty:
    def test_incoming_full_fill_resting_partial(self, engine):
        engine.books[""].add_order(_make_order("S1", "SELL", quantity=100))
        (trade,) = engine.process(_make_order("B1", "BUY", quantity=40))
        assert (trade.buy_leaves_qty, trade.sell_leaves_qty) == (0, 60)

    def test_incoming_partial_resting_full_fill(self, engine):
        engine.books[""].add_order(_make_order("B1", "BUY", quantity=30))
        (trade,) = engine.process(_make_order("S1", "SELL", quantity=100))
        assert (trade.buy_leaves_qty, trade.sell_leaves_qty) == (0, 70)

    def test_leaves_counts_down_across_a_sweep(self, engine):
        engine.books[""].add_order(_make_order("S1", "SELL", price=99.0, quantity=30))
        engine.books[""].add_order(_make_order("S2", "SELL", price=100.0, quantity=50))
        trades = engine.process(_make_order("B1", "BUY", quantity=60))
        assert [t.buy_leaves_qty for t in trades] == [30, 0]
        assert [t.sell_leaves_qty for t in trades] == [0, 20]
