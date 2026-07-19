from unittest.mock import MagicMock, patch

import pytest

from matching_engine.models import Order, Trade
from matching_engine.order_book import OrderBook
from matching_engine.producer import Producer


@pytest.fixture
def mock_exec_producer():
    with patch("matching_engine.producer.create_exec_report_producer") as mock_create:
        mock_producer = MagicMock()
        mock_create.return_value = mock_producer
        yield mock_producer


@pytest.fixture
def mock_kafka_producer(mock_exec_producer):
    with patch("matching_engine.producer.create_producer") as mock_create:
        mock_producer = MagicMock()
        mock_create.return_value = mock_producer
        yield mock_producer


@pytest.fixture
def producer(mock_kafka_producer):
    return Producer()


def _make_trade(**overrides):
    defaults = dict(
        trade_id="T1",
        symbol="AAPL",
        buy_order_id="B1",
        sell_order_id="S1",
        price=100.0,
        quantity=10,
    )
    return Trade(**{**defaults, **overrides})


class TestSendTrade:
    def test_send_trade_sends_to_trades_topic(self, producer, mock_kafka_producer):
        producer.send_trade(_make_trade())
        topic = mock_kafka_producer.send.call_args[0][0]
        assert topic == "trades"

    def test_send_trade_sends_correct_payload(self, producer, mock_kafka_producer):
        producer.send_trade(_make_trade())
        payload = mock_kafka_producer.send.call_args[0][1]
        assert payload["buy_order_id"] == "B1"
        assert payload["sell_order_id"] == "S1"
        assert payload["price"] == 100.0
        assert payload["quantity"] == 10

    def test_send_trade_called_once(self, producer, mock_kafka_producer):
        producer.send_trade(_make_trade())
        mock_kafka_producer.send.assert_called_once()


class TestSendBook:
    def test_send_book_sends_to_order_book_updates_topic(
        self, producer, mock_kafka_producer
    ):
        book = OrderBook()
        producer.send_book(book)
        topic = mock_kafka_producer.send.call_args[0][0]
        assert topic == "order_book_updates"

    def test_send_book_with_bids_and_asks(self, producer, mock_kafka_producer):
        book = OrderBook()
        book.add_order(Order("B1", "BUY", 99.0, 10))
        book.add_order(Order("S1", "SELL", 101.0, 10))
        producer.send_book(book)
        snapshot = mock_kafka_producer.send.call_args[0][1]
        assert snapshot == {"best_bid": 99.0, "best_ask": 101.0}

    def test_send_book_empty_sends_none_values(self, producer, mock_kafka_producer):
        book = OrderBook()
        producer.send_book(book)
        snapshot = mock_kafka_producer.send.call_args[0][1]
        assert snapshot == {"best_bid": None, "best_ask": None}

    def test_send_book_bids_only(self, producer, mock_kafka_producer):
        book = OrderBook()
        book.add_order(Order("B1", "BUY", 99.0, 10))
        producer.send_book(book)
        snapshot = mock_kafka_producer.send.call_args[0][1]
        assert snapshot == {"best_bid": 99.0, "best_ask": None}

    def test_send_book_asks_only(self, producer, mock_kafka_producer):
        book = OrderBook()
        book.add_order(Order("S1", "SELL", 101.0, 10))
        producer.send_book(book)
        snapshot = mock_kafka_producer.send.call_args[0][1]
        assert snapshot == {"best_bid": None, "best_ask": 101.0}

    def test_send_book_called_once(self, producer, mock_kafka_producer):
        book = OrderBook()
        producer.send_book(book)
        mock_kafka_producer.send.assert_called_once()
