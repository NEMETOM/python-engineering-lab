from matching_engine.models import Order


class TestNoMatch:
    def test_buy_with_empty_book_adds_to_book(self, engine):
        order = Order("B1", "BUY", 100.0, 10)
        trades = engine.process(order)
        assert trades == []
        assert order in engine.book.buys

    def test_sell_with_empty_book_adds_to_book(self, engine):
        order = Order("S1", "SELL", 100.0, 10)
        trades = engine.process(order)
        assert trades == []
        assert order in engine.book.sells

    def test_buy_price_below_best_ask_no_match(self, engine):
        engine.book.add_order(Order("S1", "SELL", 105.0, 10))
        buy = Order("B1", "BUY", 100.0, 10)
        trades = engine.process(buy)
        assert trades == []
        assert buy in engine.book.buys

    def test_sell_price_above_best_bid_no_match(self, engine):
        engine.book.add_order(Order("B1", "BUY", 95.0, 10))
        sell = Order("S1", "SELL", 100.0, 10)
        trades = engine.process(sell)
        assert trades == []
        assert sell in engine.book.sells


class TestBuyOrderMatching:
    def test_buy_exact_price_match_produces_one_trade(self, engine):
        engine.book.add_order(Order("S1", "SELL", 100.0, 10))
        trades = engine.process(Order("B1", "BUY", 100.0, 10))
        assert len(trades) == 1

    def test_buy_above_ask_price_produces_trade(self, engine):
        engine.book.add_order(Order("S1", "SELL", 95.0, 10))
        trades = engine.process(Order("B1", "BUY", 100.0, 10))
        assert len(trades) == 1

    def test_buy_trade_executes_at_sell_price(self, engine):
        engine.book.add_order(Order("S1", "SELL", 95.0, 10))
        trades = engine.process(Order("B1", "BUY", 100.0, 10))
        assert trades[0].price == 95.0

    def test_buy_trade_carries_correct_order_ids(self, engine):
        engine.book.add_order(Order("S1", "SELL", 100.0, 10))
        trades = engine.process(Order("B1", "BUY", 100.0, 10))
        assert trades[0].buy_order_id == "B1"
        assert trades[0].sell_order_id == "S1"

    def test_buy_trade_quantity_on_exact_fill(self, engine):
        engine.book.add_order(Order("S1", "SELL", 100.0, 10))
        trades = engine.process(Order("B1", "BUY", 100.0, 10))
        assert trades[0].quantity == 10

    def test_buy_full_fill_clears_both_sides(self, engine):
        engine.book.add_order(Order("S1", "SELL", 100.0, 10))
        engine.process(Order("B1", "BUY", 100.0, 10))
        assert engine.book.buys == []
        assert engine.book.sells == []

    def test_buy_partial_fill_remaining_added_to_book(self, engine):
        engine.book.add_order(Order("S1", "SELL", 100.0, 5))
        trades = engine.process(Order("B1", "BUY", 100.0, 10))
        assert len(trades) == 1
        assert trades[0].quantity == 5
        assert len(engine.book.buys) == 1
        assert engine.book.buys[0].quantity == 5

    def test_buy_partial_fill_sell_side_emptied(self, engine):
        engine.book.add_order(Order("S1", "SELL", 100.0, 5))
        engine.process(Order("B1", "BUY", 100.0, 10))
        assert engine.book.sells == []

    def test_buy_matches_multiple_sells(self, engine):
        engine.book.add_order(Order("S1", "SELL", 99.0, 5))
        engine.book.add_order(Order("S2", "SELL", 100.0, 5))
        trades = engine.process(Order("B1", "BUY", 100.0, 10))
        assert len(trades) == 2

    def test_buy_matches_multiple_sells_total_quantity(self, engine):
        engine.book.add_order(Order("S1", "SELL", 99.0, 3))
        engine.book.add_order(Order("S2", "SELL", 100.0, 3))
        trades = engine.process(Order("B1", "BUY", 100.0, 10))
        assert sum(t.quantity for t in trades) == 6

    def test_buy_matches_multiple_sells_remainder_in_book(self, engine):
        engine.book.add_order(Order("S1", "SELL", 99.0, 3))
        engine.book.add_order(Order("S2", "SELL", 100.0, 3))
        engine.process(Order("B1", "BUY", 100.0, 10))
        assert engine.book.buys[0].quantity == 4

    def test_buy_matches_cheapest_sell_first(self, engine):
        engine.book.add_order(Order("S1", "SELL", 100.0, 5))
        engine.book.add_order(Order("S2", "SELL", 99.0, 5))
        trades = engine.process(Order("B1", "BUY", 100.0, 5))
        assert trades[0].sell_order_id == "S2"

    def test_buy_does_not_match_sell_at_higher_price(self, engine):
        engine.book.add_order(Order("S1", "SELL", 101.0, 10))
        engine.book.add_order(Order("S2", "SELL", 105.0, 10))
        trades = engine.process(Order("B1", "BUY", 100.0, 10))
        assert trades == []


class TestSellOrderMatching:
    def test_sell_exact_price_match_produces_one_trade(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 10))
        trades = engine.process(Order("S1", "SELL", 100.0, 10))
        assert len(trades) == 1

    def test_sell_below_bid_price_produces_trade(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 10))
        trades = engine.process(Order("S1", "SELL", 95.0, 10))
        assert len(trades) == 1

    def test_sell_trade_executes_at_buy_price(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 10))
        trades = engine.process(Order("S1", "SELL", 95.0, 10))
        assert trades[0].price == 100.0

    def test_sell_trade_carries_correct_order_ids(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 10))
        trades = engine.process(Order("S1", "SELL", 100.0, 10))
        assert trades[0].buy_order_id == "B1"
        assert trades[0].sell_order_id == "S1"

    def test_sell_trade_quantity_on_exact_fill(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 10))
        trades = engine.process(Order("S1", "SELL", 100.0, 10))
        assert trades[0].quantity == 10

    def test_sell_full_fill_clears_both_sides(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 10))
        engine.process(Order("S1", "SELL", 100.0, 10))
        assert engine.book.buys == []
        assert engine.book.sells == []

    def test_sell_partial_fill_remaining_added_to_book(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 5))
        trades = engine.process(Order("S1", "SELL", 100.0, 10))
        assert len(trades) == 1
        assert trades[0].quantity == 5
        assert len(engine.book.sells) == 1
        assert engine.book.sells[0].quantity == 5

    def test_sell_partial_fill_buy_side_emptied(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 5))
        engine.process(Order("S1", "SELL", 100.0, 10))
        assert engine.book.buys == []

    def test_sell_matches_multiple_buys(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 5))
        engine.book.add_order(Order("B2", "BUY", 99.0, 5))
        trades = engine.process(Order("S1", "SELL", 99.0, 10))
        assert len(trades) == 2

    def test_sell_matches_multiple_buys_total_quantity(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 3))
        engine.book.add_order(Order("B2", "BUY", 99.0, 3))
        trades = engine.process(Order("S1", "SELL", 99.0, 10))
        assert sum(t.quantity for t in trades) == 6

    def test_sell_matches_multiple_buys_remainder_in_book(self, engine):
        engine.book.add_order(Order("B1", "BUY", 100.0, 3))
        engine.book.add_order(Order("B2", "BUY", 99.0, 3))
        engine.process(Order("S1", "SELL", 99.0, 10))
        assert engine.book.sells[0].quantity == 4

    def test_sell_matches_highest_bid_first(self, engine):
        engine.book.add_order(Order("B1", "BUY", 99.0, 5))
        engine.book.add_order(Order("B2", "BUY", 100.0, 5))
        trades = engine.process(Order("S1", "SELL", 99.0, 5))
        assert trades[0].buy_order_id == "B2"

    def test_sell_does_not_match_buy_at_lower_price(self, engine):
        engine.book.add_order(Order("B1", "BUY", 95.0, 10))
        engine.book.add_order(Order("B2", "BUY", 90.0, 10))
        trades = engine.process(Order("S1", "SELL", 100.0, 10))
        assert trades == []
