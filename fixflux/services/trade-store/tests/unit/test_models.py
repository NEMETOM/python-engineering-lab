from sqlalchemy import DateTime, Float, Integer

from trade_store.models import TradeModel


class TestTradeModelTable:
    def test_tablename_is_trades(self):
        assert TradeModel.__tablename__ == "trades"


class TestTradeModelColumns:
    def test_trade_id_column_exists(self):
        assert "trade_id" in TradeModel.__table__.c

    def test_symbol_column_exists(self):
        assert "symbol" in TradeModel.__table__.c

    def test_buy_order_id_column_exists(self):
        assert "buy_order_id" in TradeModel.__table__.c

    def test_sell_order_id_column_exists(self):
        assert "sell_order_id" in TradeModel.__table__.c

    def test_price_column_exists(self):
        assert "price" in TradeModel.__table__.c

    def test_quantity_column_exists(self):
        assert "quantity" in TradeModel.__table__.c

    def test_timestamp_column_exists(self):
        assert "timestamp" in TradeModel.__table__.c

    def test_trade_id_is_primary_key(self):
        assert TradeModel.__table__.c["trade_id"].primary_key

    def test_price_is_float_type(self):
        assert isinstance(TradeModel.__table__.c["price"].type, Float)

    def test_quantity_is_integer_type(self):
        assert isinstance(TradeModel.__table__.c["quantity"].type, Integer)

    def test_timestamp_is_datetime_type(self):
        assert isinstance(TradeModel.__table__.c["timestamp"].type, DateTime)
