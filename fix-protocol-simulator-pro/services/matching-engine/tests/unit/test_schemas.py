from datetime import datetime

import pytest
from pydantic import ValidationError

from matching_engine.schemas.book_event import BookEvent
from matching_engine.schemas.order_event import OrderEvent
from matching_engine.schemas.trade_event import TradeEvent


class TestOrderEvent:
    def test_valid_buy_order_event(self):
        event = OrderEvent(
            order_id="O1", symbol="BTCUSD", side="BUY", price=100.0, quantity=10
        )
        assert event.order_id == "O1"
        assert event.symbol == "BTCUSD"
        assert event.side == "BUY"
        assert event.price == 100.0
        assert event.quantity == 10

    def test_valid_sell_order_event(self):
        event = OrderEvent(
            order_id="O2", symbol="BTCUSD", side="SELL", price=100.0, quantity=10
        )
        assert event.side == "SELL"

    def test_timestamp_defaulted_automatically(self):
        event = OrderEvent(
            order_id="O1", symbol="BTCUSD", side="BUY", price=100.0, quantity=10
        )
        assert isinstance(event.timestamp, datetime)

    def test_invalid_side_raises(self):
        with pytest.raises(ValidationError):
            OrderEvent(
                order_id="O1", symbol="BTCUSD", side="HOLD", price=100.0, quantity=10
            )

    def test_zero_price_raises(self):
        with pytest.raises(ValidationError):
            OrderEvent(
                order_id="O1", symbol="BTCUSD", side="BUY", price=0.0, quantity=10
            )

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError):
            OrderEvent(
                order_id="O1", symbol="BTCUSD", side="BUY", price=-1.0, quantity=10
            )

    def test_zero_quantity_raises(self):
        with pytest.raises(ValidationError):
            OrderEvent(
                order_id="O1", symbol="BTCUSD", side="BUY", price=100.0, quantity=0
            )

    def test_negative_quantity_raises(self):
        with pytest.raises(ValidationError):
            OrderEvent(
                order_id="O1", symbol="BTCUSD", side="BUY", price=100.0, quantity=-5
            )

    def test_missing_order_id_raises(self):
        with pytest.raises(ValidationError):
            OrderEvent(symbol="BTCUSD", side="BUY", price=100.0, quantity=10)

    def test_missing_symbol_raises(self):
        with pytest.raises(ValidationError):
            OrderEvent(order_id="O1", side="BUY", price=100.0, quantity=10)

    def test_missing_price_raises(self):
        with pytest.raises(ValidationError):
            OrderEvent(order_id="O1", symbol="BTCUSD", side="BUY", quantity=10)

    def test_missing_quantity_raises(self):
        with pytest.raises(ValidationError):
            OrderEvent(order_id="O1", symbol="BTCUSD", side="BUY", price=100.0)


class TestTradeEvent:
    def test_valid_trade_event(self):
        event = TradeEvent(
            trade_id="T1",
            symbol="BTCUSD",
            buy_order_id="B1",
            sell_order_id="S1",
            price=100.0,
            quantity=10,
        )
        assert event.trade_id == "T1"
        assert event.buy_order_id == "B1"
        assert event.sell_order_id == "S1"
        assert event.price == 100.0
        assert event.quantity == 10

    def test_timestamp_defaulted_automatically(self):
        event = TradeEvent(
            trade_id="T1",
            symbol="BTCUSD",
            buy_order_id="B1",
            sell_order_id="S1",
            price=100.0,
            quantity=10,
        )
        assert isinstance(event.timestamp, datetime)

    def test_missing_trade_id_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                symbol="BTCUSD",
                buy_order_id="B1",
                sell_order_id="S1",
                price=100.0,
                quantity=10,
            )

    def test_missing_symbol_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                trade_id="T1",
                buy_order_id="B1",
                sell_order_id="S1",
                price=100.0,
                quantity=10,
            )

    def test_missing_price_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                trade_id="T1",
                symbol="BTCUSD",
                buy_order_id="B1",
                sell_order_id="S1",
                quantity=10,
            )

    def test_missing_quantity_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                trade_id="T1",
                symbol="BTCUSD",
                buy_order_id="B1",
                sell_order_id="S1",
                price=100.0,
            )

    def test_missing_buy_order_id_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                trade_id="T1",
                symbol="BTCUSD",
                sell_order_id="S1",
                price=100.0,
                quantity=10,
            )

    def test_missing_sell_order_id_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                trade_id="T1",
                symbol="BTCUSD",
                buy_order_id="B1",
                price=100.0,
                quantity=10,
            )


class TestBookEvent:
    def test_valid_book_event_with_both_sides(self):
        event = BookEvent(symbol="BTCUSD", best_bid=99.0, best_ask=101.0)
        assert event.symbol == "BTCUSD"
        assert event.best_bid == 99.0
        assert event.best_ask == 101.0

    def test_best_bid_defaults_to_none(self):
        event = BookEvent(symbol="BTCUSD", best_ask=101.0)
        assert event.best_bid is None

    def test_best_ask_defaults_to_none(self):
        event = BookEvent(symbol="BTCUSD", best_bid=99.0)
        assert event.best_ask is None

    def test_both_sides_can_be_none(self):
        event = BookEvent(symbol="BTCUSD")
        assert event.best_bid is None
        assert event.best_ask is None

    def test_timestamp_defaulted_automatically(self):
        event = BookEvent(symbol="BTCUSD")
        assert isinstance(event.timestamp, datetime)

    def test_missing_symbol_raises(self):
        with pytest.raises(ValidationError):
            BookEvent(best_bid=99.0, best_ask=101.0)
