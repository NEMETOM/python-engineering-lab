from unittest.mock import MagicMock, patch

from market_data_service.publisher import MarketPublisher


def _make_snapshot(**overrides):
    base = {"best_bid": 99.50, "best_ask": 100.50, "last_trade_price": 100.0}
    return {**base, **overrides}


class TestPublish:
    @patch("market_data_service.publisher.create_producer")
    def test_publish_calls_snapshot(self, _):
        mock_cache = MagicMock()
        mock_cache.snapshot.return_value = _make_snapshot()
        publisher = MarketPublisher(mock_cache)
        publisher.publish()
        mock_cache.snapshot.assert_called_once()

    @patch("market_data_service.publisher.create_producer")
    def test_publishes_to_market_data_topic(self, mock_create_producer):
        mock_producer = MagicMock()
        mock_create_producer.return_value = mock_producer
        mock_cache = MagicMock()
        mock_cache.snapshot.return_value = _make_snapshot()
        publisher = MarketPublisher(mock_cache)
        publisher.publish()
        assert mock_producer.send.call_args[0][0] == "market_data"

    @patch("market_data_service.publisher.create_producer")
    def test_skips_when_no_data(self, mock_create_producer):
        mock_producer = MagicMock()
        mock_create_producer.return_value = mock_producer
        mock_cache = MagicMock()
        mock_cache.snapshot.return_value = _make_snapshot(best_bid=None, best_ask=None, last_trade_price=None)
        publisher = MarketPublisher(mock_cache)
        publisher.publish()
        mock_producer.send.assert_not_called()

    @patch("market_data_service.publisher.create_producer")
    def test_skips_when_snapshot_unchanged(self, mock_create_producer):
        mock_producer = MagicMock()
        mock_create_producer.return_value = mock_producer
        mock_cache = MagicMock()
        mock_cache.snapshot.return_value = _make_snapshot()
        publisher = MarketPublisher(mock_cache)
        publisher.publish()
        publisher.publish()
        assert mock_producer.send.call_count == 1

    @patch("market_data_service.publisher.create_producer")
    def test_publishes_when_snapshot_changes(self, mock_create_producer):
        mock_producer = MagicMock()
        mock_create_producer.return_value = mock_producer
        mock_cache = MagicMock()
        mock_cache.snapshot.side_effect = [_make_snapshot(best_bid=99.0), _make_snapshot(best_bid=99.5)]
        publisher = MarketPublisher(mock_cache)
        publisher.publish()
        publisher.publish()
        assert mock_producer.send.call_count == 2
