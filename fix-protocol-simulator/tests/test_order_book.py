#fix-protocol-simulator/tests/test_order_book.py

from fix_simulator.exchange.order_book import OrderBook
from fix_simulator.exchange.order import Order


def test_best_bid():
    book = OrderBook()
    book.add_order(Order("1", "BUY", 100, 10))
    book.add_order(Order("2", "BUY", 105, 5))
    assert book.best_bid().price == 105


def test_best_ask():
    book = OrderBook()
    book.add_order(Order("1", "SELL", 100, 10))
    book.add_order(Order("2", "SELL", 95, 5))
    assert book.best_ask().price == 95


def test_best_bid_empty():
    book = OrderBook()
    assert book.best_bid() is None


def test_best_ask_empty():
    book = OrderBook()
    assert book.best_ask() is None


def test_add_order_routes_by_side():
    book = OrderBook()
    book.add_order(Order("1", "BUY", 100, 10))
    book.add_order(Order("2", "SELL", 110, 5))
    assert len(book.bids) == 1
    assert len(book.asks) == 1
