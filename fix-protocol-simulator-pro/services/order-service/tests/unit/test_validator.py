from datetime import datetime
from unittest.mock import MagicMock

import pytest
from order_service.schemas import RawOrderEvent
from order_service.validator import OrderValidator
from shared.exceptions import ValidationError


def _make_event(**overrides):
    defaults = dict(
        symbol="AAPL", side="BUY", price=100.0, quantity=10, timestamp=datetime.utcnow()
    )
    return RawOrderEvent(**{**defaults, **overrides})


class TestValidOrder:
    def test_buy_order_passes(self):
        validator = OrderValidator()
        assert validator.validate(_make_event(side="BUY")) is True

    def test_sell_order_passes(self):
        validator = OrderValidator()
        assert validator.validate(_make_event(side="SELL")) is True


class TestPriceValidation:
    def test_zero_price_raises(self):
        validator = OrderValidator()
        with pytest.raises(ValidationError, match="price must be positive"):
            validator.validate(_make_event(price=0))

    def test_negative_price_raises(self):
        validator = OrderValidator()
        with pytest.raises(ValidationError, match="price must be positive"):
            validator.validate(_make_event(price=-1.0))


class TestQuantityValidation:
    def test_zero_quantity_raises(self):
        validator = OrderValidator()
        with pytest.raises(ValidationError, match="quantity must be positive"):
            validator.validate(_make_event(quantity=0))

    def test_negative_quantity_raises(self):
        validator = OrderValidator()
        with pytest.raises(ValidationError, match="quantity must be positive"):
            validator.validate(_make_event(quantity=-5))


def _make_mock_order(side, price=100.0, quantity=10):
    m = MagicMock()
    m.side = side
    m.price = price
    m.quantity = quantity
    return m


class TestSideValidation:
    def test_invalid_side_raises(self):
        validator = OrderValidator()
        with pytest.raises(ValidationError, match="invalid side"):
            validator.validate(_make_mock_order(side="HOLD"))

    def test_lowercase_buy_raises(self):
        validator = OrderValidator()
        with pytest.raises(ValidationError, match="invalid side"):
            validator.validate(_make_mock_order(side="buy"))

    def test_lowercase_sell_raises(self):
        validator = OrderValidator()
        with pytest.raises(ValidationError, match="invalid side"):
            validator.validate(_make_mock_order(side="sell"))
