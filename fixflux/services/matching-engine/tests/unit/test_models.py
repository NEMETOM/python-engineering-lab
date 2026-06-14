from matching_engine.models import Order, Trade


class TestOrder:
    def test_order_creation_stores_all_fields(self):
        order = Order(order_id="O1", side="BUY", price=100.0, quantity=10)
        assert order.order_id == "O1"
        assert order.side == "BUY"
        assert order.price == 100.0
        assert order.quantity == 10

    def test_order_sell_side(self):
        order = Order(order_id="O2", side="SELL", price=50.0, quantity=5)
        assert order.side == "SELL"

    def test_order_quantity_is_mutable(self):
        order = Order(order_id="O1", side="BUY", price=100.0, quantity=10)
        order.quantity = 5
        assert order.quantity == 5

    def test_order_price_is_mutable(self):
        order = Order(order_id="O1", side="BUY", price=100.0, quantity=10)
        order.price = 99.5
        assert order.price == 99.5


class TestTrade:
    def test_trade_creation_stores_all_fields(self):
        trade = Trade(
            trade_id="T1",
            symbol="AAPL",
            buy_order_id="B1",
            sell_order_id="S1",
            price=100.0,
            quantity=10,
        )
        assert trade.trade_id == "T1"
        assert trade.symbol == "AAPL"
        assert trade.buy_order_id == "B1"
        assert trade.sell_order_id == "S1"
        assert trade.price == 100.0
        assert trade.quantity == 10

    def test_trade_dict_contains_all_fields(self):
        trade = Trade(
            trade_id="T1",
            symbol="AAPL",
            buy_order_id="B1",
            sell_order_id="S1",
            price=100.0,
            quantity=10,
        )
        d = trade.__dict__
        assert d["trade_id"] == "T1"
        assert d["symbol"] == "AAPL"
        assert d["buy_order_id"] == "B1"
        assert d["sell_order_id"] == "S1"
        assert d["price"] == 100.0
        assert d["quantity"] == 10
