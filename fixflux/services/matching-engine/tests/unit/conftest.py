import pytest

from matching_engine.engine import MatchingEngine
from matching_engine.models import Order
from matching_engine.order_book import OrderBook


@pytest.fixture
def empty_book():
    return OrderBook()


@pytest.fixture
def engine():
    return MatchingEngine()


@pytest.fixture
def buy_order():
    return Order(order_id="B1", side="BUY", price=100.0, quantity=10)


@pytest.fixture
def sell_order():
    return Order(order_id="S1", side="SELL", price=100.0, quantity=10)
