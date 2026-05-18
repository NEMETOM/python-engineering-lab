from unittest.mock import MagicMock, patch

import pytest
from market_data_service.consumer import run


def _poll_result(value):
    record = MagicMock()
    record.value = value
    return {"tp": [record]}


class TestRun:
    def test_publishes_when_book_update_received(self):
        with patch(
            "market_data_service.consumer.create_consumer"
        ) as mock_create, patch(
            "market_data_service.consumer.MarketPublisher"
        ) as mock_publisher_cls:
            book_consumer = MagicMock()
            trade_consumer = MagicMock()
            mock_create.side_effect = [book_consumer, trade_consumer]
            book_consumer.poll.side_effect = [
                _poll_result({"best_bid": 99.0, "best_ask": 101.0}),
                StopIteration,
            ]
            trade_consumer.poll.return_value = {}
            mock_publisher = mock_publisher_cls.return_value
            with pytest.raises(StopIteration):
                run()
            mock_publisher.publish.assert_called_once()

    def test_publishes_when_trade_received(self):
        with patch(
            "market_data_service.consumer.create_consumer"
        ) as mock_create, patch(
            "market_data_service.consumer.MarketPublisher"
        ) as mock_publisher_cls:
            book_consumer = MagicMock()
            trade_consumer = MagicMock()
            mock_create.side_effect = [book_consumer, trade_consumer]
            book_consumer.poll.return_value = {}
            trade_consumer.poll.side_effect = [
                _poll_result({"price": 100.0}),
                StopIteration,
            ]
            mock_publisher = mock_publisher_cls.return_value
            with pytest.raises(StopIteration):
                run()
            mock_publisher.publish.assert_called_once()

    def test_no_publish_when_no_messages(self):
        with patch(
            "market_data_service.consumer.create_consumer"
        ) as mock_create, patch(
            "market_data_service.consumer.MarketPublisher"
        ) as mock_publisher_cls:
            book_consumer = MagicMock()
            trade_consumer = MagicMock()
            mock_create.side_effect = [book_consumer, trade_consumer]
            book_consumer.poll.side_effect = [{}, StopIteration]
            trade_consumer.poll.return_value = {}
            mock_publisher = mock_publisher_cls.return_value
            with pytest.raises(StopIteration):
                run()
            mock_publisher.publish.assert_not_called()
