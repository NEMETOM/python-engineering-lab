import uuid
from datetime import datetime

from order_service.schemas import RawOrderEvent
from order_service.transformer import OrderTransformer


def _make_raw(**overrides):
    defaults = dict(
        symbol="AAPL", side="BUY", price=100.0, quantity=10, timestamp=datetime.utcnow()
    )
    return RawOrderEvent(**{**defaults, **overrides})


class TestTransformOutputFields:
    def setup_method(self):
        self.transformer = OrderTransformer()
        self.raw = _make_raw()
        self.result = self.transformer.transform(self.raw)

    def test_order_id_is_set(self):
        assert self.result.order_id is not None

    def test_order_id_is_valid_uuid(self):
        uuid.UUID(self.result.order_id)

    def test_symbol_is_preserved(self):
        assert self.result.symbol == self.raw.symbol

    def test_side_is_preserved(self):
        assert self.result.side == self.raw.side

    def test_price_is_preserved(self):
        assert self.result.price == self.raw.price

    def test_quantity_is_preserved(self):
        assert self.result.quantity == self.raw.quantity

    def test_timestamp_is_set(self):
        assert self.result.timestamp is not None

    def test_sell_side_is_preserved(self):
        raw = _make_raw(side="SELL")
        result = self.transformer.transform(raw)
        assert result.side == "SELL"


class TestTransformUniqueness:
    def test_each_call_generates_unique_order_id(self):
        transformer = OrderTransformer()
        raw = _make_raw()
        r1 = transformer.transform(raw)
        r2 = transformer.transform(raw)
        assert r1.order_id != r2.order_id
