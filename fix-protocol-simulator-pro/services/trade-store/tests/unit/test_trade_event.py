from datetime import datetime

import pytest
from pydantic import ValidationError
from trade_store.schemas.trade_event import TradeEvent


def _make_event(**overrides):
    defaults = dict(
        trade_id="T001",
        symbol="AAPL",
        buy_order_id="B001",
        sell_order_id="S001",
        price=150.0,
        quantity=10,
        timestamp=datetime.utcnow(),
    )
    return TradeEvent(**{**defaults, **overrides})


class TestValidTradeEvent:
    def test_valid_event_creates_successfully(self):
        event = _make_event()
        assert event.trade_id == "T001"
        assert event.symbol == "AAPL"
        assert event.price == 150.0
        assert event.quantity == 10

    def test_timestamp_as_string_is_coerced(self):
        event = _make_event(timestamp="2024-01-15T10:30:00")
        assert isinstance(event.timestamp, datetime)

    def test_price_as_integer_is_coerced_to_float(self):
        event = _make_event(price=100)
        assert isinstance(event.price, float)

    def test_all_fields_stored_correctly(self):
        ts = datetime(2024, 1, 15, 10, 30, 0)
        event = _make_event(
            trade_id="T999",
            symbol="MSFT",
            buy_order_id="B999",
            sell_order_id="S999",
            price=200.5,
            quantity=5,
            timestamp=ts,
        )
        assert event.trade_id == "T999"
        assert event.symbol == "MSFT"
        assert event.buy_order_id == "B999"
        assert event.sell_order_id == "S999"
        assert event.price == 200.5
        assert event.quantity == 5
        assert event.timestamp == ts


class TestMissingFields:
    def test_missing_trade_id_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                symbol="AAPL",
                buy_order_id="B1",
                sell_order_id="S1",
                price=10.0,
                quantity=1,
                timestamp=datetime.utcnow(),
            )

    def test_missing_symbol_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                trade_id="T1",
                buy_order_id="B1",
                sell_order_id="S1",
                price=10.0,
                quantity=1,
                timestamp=datetime.utcnow(),
            )

    def test_missing_price_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                trade_id="T1",
                symbol="AAPL",
                buy_order_id="B1",
                sell_order_id="S1",
                quantity=1,
                timestamp=datetime.utcnow(),
            )

    def test_missing_quantity_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                trade_id="T1",
                symbol="AAPL",
                buy_order_id="B1",
                sell_order_id="S1",
                price=10.0,
                timestamp=datetime.utcnow(),
            )


class TestInvalidFieldTypes:
    def test_non_numeric_price_raises(self):
        with pytest.raises(ValidationError):
            _make_event(price="not-a-number")

    def test_non_integer_quantity_raises(self):
        with pytest.raises(ValidationError):
            _make_event(quantity="many")

    def test_invalid_timestamp_raises(self):
        with pytest.raises(ValidationError):
            _make_event(timestamp="not-a-date")
