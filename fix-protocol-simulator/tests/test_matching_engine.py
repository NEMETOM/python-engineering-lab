# fix-protocol-simulator/tests/test_matching_engine.py

from fix_simulator.exchange.matching_engine import MatchingEngine
from fix_simulator.exchange.order import Order
from fix_simulator.exchange.order_book import OrderBook


def test_matching_trade():
    book = OrderBook()
    engine = MatchingEngine(book)
    engine.process_order(Order("1", "BUY", 100, 10))
    trade = engine.process_order(Order("2", "SELL", 100, 10))
    assert trade["price"] == 100
    assert trade["quantity"] == 10


def test_no_trade_when_prices_dont_cross():
    book = OrderBook()
    engine = MatchingEngine(book)
    engine.process_order(Order("1", "BUY", 90, 10))
    trade = engine.process_order(Order("2", "SELL", 100, 10))
    assert trade is None


def test_partial_quantity_trade():
    book = OrderBook()
    engine = MatchingEngine(book)
    engine.process_order(Order("1", "BUY", 100, 3))
    trade = engine.process_order(Order("2", "SELL", 100, 10))
    assert trade["quantity"] == 3


def test_sell_matches_best_bid():
    book = OrderBook()
    engine = MatchingEngine(book)
    engine.process_order(Order("1", "BUY", 100, 5))
    engine.process_order(Order("2", "BUY", 105, 5))
    trade = engine.process_order(Order("3", "SELL", 100, 5))
    assert trade["price"] == 105


def test_buy_matches_best_ask():
    book = OrderBook()
    engine = MatchingEngine(book)
    engine.process_order(Order("1", "SELL", 100, 5))
    trade = engine.process_order(Order("2", "BUY", 100, 5))
    assert trade["price"] == 100
    assert trade["quantity"] == 5


def test_unmatched_order_added_to_book():
    book = OrderBook()
    engine = MatchingEngine(book)
    engine.process_order(Order("1", "BUY", 90, 10))
    assert book.best_bid().price == 90
