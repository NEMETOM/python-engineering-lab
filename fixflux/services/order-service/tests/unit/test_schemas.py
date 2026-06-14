from datetime import datetime

import pytest
from pydantic import ValidationError

from order_service.schemas import RawOrderEvent, ValidatedOrderEvent


def _now():
    return datetime.utcnow()


class TestRawOrderEvent:
    def test_valid_raw_order_event(self):
        event = RawOrderEvent(
            symbol="AAPL", side="BUY", price=100.0, quantity=10, timestamp=_now()
        )
        assert event.symbol == "AAPL"
        assert event.side == "BUY"
        assert event.price == 100.0
        assert event.quantity == 10

    def test_missing_symbol_raises(self):
        with pytest.raises(ValidationError):
            RawOrderEvent(side="BUY", price=100.0, quantity=10, timestamp=_now())

    def test_missing_side_raises(self):
        with pytest.raises(ValidationError):
            RawOrderEvent(symbol="AAPL", price=100.0, quantity=10, timestamp=_now())

    def test_missing_price_raises(self):
        with pytest.raises(ValidationError):
            RawOrderEvent(symbol="AAPL", side="BUY", quantity=10, timestamp=_now())

    def test_missing_quantity_raises(self):
        with pytest.raises(ValidationError):
            RawOrderEvent(symbol="AAPL", side="BUY", price=100.0, timestamp=_now())

    def test_missing_timestamp_raises(self):
        with pytest.raises(ValidationError):
            RawOrderEvent(symbol="AAPL", side="BUY", price=100.0, quantity=10)


class TestValidatedOrderEvent:
    def test_valid_validated_order_event(self):
        event = ValidatedOrderEvent(
            order_id="abc",
            symbol="AAPL",
            side="BUY",
            price=100.0,
            quantity=10,
            timestamp=_now(),
        )
        assert event.order_id == "abc"

    def test_zero_price_raises(self):
        with pytest.raises(ValidationError):
            ValidatedOrderEvent(
                order_id="abc",
                symbol="AAPL",
                side="BUY",
                price=0,
                quantity=10,
                timestamp=_now(),
            )

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError):
            ValidatedOrderEvent(
                order_id="abc",
                symbol="AAPL",
                side="BUY",
                price=-1.0,
                quantity=10,
                timestamp=_now(),
            )

    def test_zero_quantity_raises(self):
        with pytest.raises(ValidationError):
            ValidatedOrderEvent(
                order_id="abc",
                symbol="AAPL",
                side="BUY",
                price=100.0,
                quantity=0,
                timestamp=_now(),
            )

    def test_negative_quantity_raises(self):
        with pytest.raises(ValidationError):
            ValidatedOrderEvent(
                order_id="abc",
                symbol="AAPL",
                side="BUY",
                price=100.0,
                quantity=-5,
                timestamp=_now(),
            )

    def test_invalid_side_raises(self):
        with pytest.raises(ValidationError):
            ValidatedOrderEvent(
                order_id="abc",
                symbol="AAPL",
                side="HOLD",
                price=100.0,
                quantity=10,
                timestamp=_now(),
            )

    def test_missing_order_id_raises(self):
        with pytest.raises(ValidationError):
            ValidatedOrderEvent(
                symbol="AAPL", side="BUY", price=100.0, quantity=10, timestamp=_now()
            )
