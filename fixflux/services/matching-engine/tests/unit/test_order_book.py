from matching_engine.models import Order


class TestAddOrder:
    def test_buy_order_goes_into_buys_list(self, empty_book):
        order = Order("B1", "BUY", 100.0, 10)
        empty_book.add_order(order)
        assert order in empty_book.buys
        assert order not in empty_book.sells

    def test_sell_order_goes_into_sells_list(self, empty_book):
        order = Order("S1", "SELL", 100.0, 10)
        empty_book.add_order(order)
        assert order in empty_book.sells
        assert order not in empty_book.buys

    def test_buy_orders_sorted_descending_by_price(self, empty_book):
        empty_book.add_order(Order("B1", "BUY", 90.0, 5))
        empty_book.add_order(Order("B2", "BUY", 100.0, 5))
        empty_book.add_order(Order("B3", "BUY", 95.0, 5))
        prices = [o.price for o in empty_book.buys]
        assert prices == sorted(prices, reverse=True)

    def test_sell_orders_sorted_ascending_by_price(self, empty_book):
        empty_book.add_order(Order("S1", "SELL", 110.0, 5))
        empty_book.add_order(Order("S2", "SELL", 100.0, 5))
        empty_book.add_order(Order("S3", "SELL", 105.0, 5))
        prices = [o.price for o in empty_book.sells]
        assert prices == sorted(prices)

    def test_single_buy_order_count(self, empty_book):
        empty_book.add_order(Order("B1", "BUY", 100.0, 10))
        assert len(empty_book.buys) == 1

    def test_single_sell_order_count(self, empty_book):
        empty_book.add_order(Order("S1", "SELL", 100.0, 10))
        assert len(empty_book.sells) == 1

    def test_multiple_buy_orders_all_stored(self, empty_book):
        for i in range(5):
            empty_book.add_order(Order(f"B{i}", "BUY", 100.0 + i, 10))
        assert len(empty_book.buys) == 5

    def test_multiple_sell_orders_all_stored(self, empty_book):
        for i in range(5):
            empty_book.add_order(Order(f"S{i}", "SELL", 100.0 + i, 10))
        assert len(empty_book.sells) == 5

    def test_buy_orders_at_same_price_both_stored(self, empty_book):
        empty_book.add_order(Order("B1", "BUY", 100.0, 5))
        empty_book.add_order(Order("B2", "BUY", 100.0, 5))
        assert len(empty_book.buys) == 2


class TestBestBid:
    def test_best_bid_empty_book_returns_none(self, empty_book):
        assert empty_book.best_bid() is None

    def test_best_bid_single_order_returns_it(self, empty_book):
        order = Order("B1", "BUY", 100.0, 10)
        empty_book.add_order(order)
        assert empty_book.best_bid() == order

    def test_best_bid_returns_highest_price(self, empty_book):
        empty_book.add_order(Order("B1", "BUY", 90.0, 5))
        empty_book.add_order(Order("B2", "BUY", 100.0, 5))
        empty_book.add_order(Order("B3", "BUY", 95.0, 5))
        assert empty_book.best_bid().price == 100.0

    def test_best_bid_unaffected_by_sell_orders(self, empty_book):
        empty_book.add_order(Order("B1", "BUY", 100.0, 10))
        empty_book.add_order(Order("S1", "SELL", 50.0, 10))
        assert empty_book.best_bid().price == 100.0


class TestBestAsk:
    def test_best_ask_empty_book_returns_none(self, empty_book):
        assert empty_book.best_ask() is None

    def test_best_ask_single_order_returns_it(self, empty_book):
        order = Order("S1", "SELL", 100.0, 10)
        empty_book.add_order(order)
        assert empty_book.best_ask() == order

    def test_best_ask_returns_lowest_price(self, empty_book):
        empty_book.add_order(Order("S1", "SELL", 110.0, 5))
        empty_book.add_order(Order("S2", "SELL", 100.0, 5))
        empty_book.add_order(Order("S3", "SELL", 105.0, 5))
        assert empty_book.best_ask().price == 100.0

    def test_best_ask_unaffected_by_buy_orders(self, empty_book):
        empty_book.add_order(Order("S1", "SELL", 100.0, 10))
        empty_book.add_order(Order("B1", "BUY", 200.0, 10))
        assert empty_book.best_ask().price == 100.0
