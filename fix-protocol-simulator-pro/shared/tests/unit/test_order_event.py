from datetime import datetime

import pytest
from pydantic import ValidationError as PydanticValidationError
from shared.schemas.order_event import OrderEvent


def _make(**overrides):
    defaults = dict(order_id="O1", symbol="AAPL", side="BUY", price=100.0, quantity=10)
    return OrderEvent(**{**defaults, **overrides})


class TestValidOrderEvent:
    def test_buy_side_accepted(self):
        event = _make(side="BUY")
        assert event.side == "BUY"

    def test_sell_side_accepted(self):
        event = _make(side="SELL")
        assert event.side == "SELL"

    def test_all_fields_stored(self):
        event = _make(
            order_id="O99", symbol="MSFT", side="SELL", price=200.5, quantity=5
        )
        assert event.order_id == "O99"
        assert event.symbol == "MSFT"
        assert event.price == 200.5
        assert event.quantity == 5

    def test_timestamp_defaults_to_now(self):
        event = _make()
        assert isinstance(event.timestamp, datetime)


class TestInvalidSide:
    def test_unknown_literal_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(side="HOLD")

    def test_lowercase_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(side="buy")

    def test_empty_string_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(side="")


class TestInvalidPrice:
    def test_zero_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(price=0)

    def test_negative_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(price=-1.0)


class TestInvalidQuantity:
    def test_zero_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(quantity=0)

    def test_negative_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(quantity=-5)


class TestMissingFields:
    @pytest.mark.parametrize(
        "field", ["order_id", "symbol", "side", "price", "quantity"]
    )
    def test_missing_required_field_raises(self, field):
        data = dict(order_id="O1", symbol="AAPL", side="BUY", price=100.0, quantity=10)
        del data[field]
        with pytest.raises(PydanticValidationError):
            OrderEvent(**data)
