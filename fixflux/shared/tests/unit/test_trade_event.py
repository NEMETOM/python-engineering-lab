from datetime import datetime

import pytest
from pydantic import ValidationError as PydanticValidationError
from shared.schemas.trade_event import TradeEvent


def _make(**overrides):
    defaults = dict(
        trade_id="T001",
        symbol="AAPL",
        buy_order_id="B001",
        sell_order_id="S001",
        price=150.0,
        quantity=10,
    )
    return TradeEvent(**{**defaults, **overrides})


class TestValidTradeEvent:
    def test_valid_event_created(self):
        event = _make()
        assert event.trade_id == "T001"

    def test_all_fields_stored(self):
        event = _make(trade_id="T999", symbol="MSFT", price=200.5, quantity=5)
        assert event.trade_id == "T999"
        assert event.symbol == "MSFT"
        assert event.price == 200.5
        assert event.quantity == 5

    def test_order_ids_stored(self):
        event = _make(buy_order_id="B99", sell_order_id="S99")
        assert event.buy_order_id == "B99"
        assert event.sell_order_id == "S99"

    def test_timestamp_defaults_to_now(self):
        event = _make()
        assert isinstance(event.timestamp, datetime)

    def test_explicit_timestamp_accepted(self):
        ts = datetime(2024, 1, 15, 10, 30, 0)
        event = _make(timestamp=ts)
        assert event.timestamp == ts


class TestMissingFields:
    @pytest.mark.parametrize(
        "field",
        ["trade_id", "symbol", "buy_order_id", "sell_order_id", "price", "quantity"],
    )
    def test_missing_required_field_raises(self, field):
        data = dict(
            trade_id="T001",
            symbol="AAPL",
            buy_order_id="B001",
            sell_order_id="S001",
            price=150.0,
            quantity=10,
        )
        del data[field]
        with pytest.raises(PydanticValidationError):
            TradeEvent(**data)


class TestInvalidFieldTypes:
    def test_non_numeric_price_raises(self):
        with pytest.raises(PydanticValidationError):
            _make(price="not-a-number")

    def test_non_integer_quantity_raises(self):
        with pytest.raises(PydanticValidationError):
            _make(quantity="many")

    def test_invalid_timestamp_raises(self):
        with pytest.raises(PydanticValidationError):
            _make(timestamp="not-a-date")
