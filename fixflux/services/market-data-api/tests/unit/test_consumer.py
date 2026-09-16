import asyncio
from unittest.mock import MagicMock, patch

from market_data_api.consumer import MarketDataConsumer


def _msg(value):
    m = MagicMock()
    m.value = value
    return m


_VALID_EVENT = {
    "symbol": "AAPL",
    "best_bid": 175.0,
    "best_ask": 175.5,
    "mid_price": 175.25,
    "last_trade_price": 175.0,
    "timestamp": "2026-01-01T00:00:00Z",
}


class TestConstruction:
    @patch("market_data_api.consumer.create_consumer")
    def test_consumes_market_data_topic_with_its_own_group(self, mock_create):
        loop = asyncio.new_event_loop()
        MarketDataConsumer(MagicMock(), loop)
        mock_create.assert_called_once_with("market_data", "market-data-api")
        loop.close()


class TestRun:
    @patch("market_data_api.consumer.asyncio.run_coroutine_threadsafe")
    @patch("market_data_api.consumer.create_consumer")
    def test_valid_message_is_broadcast(self, mock_create, mock_run_threadsafe):
        mock_create.return_value = [_msg(_VALID_EVENT)]
        manager = MagicMock()
        loop = MagicMock()
        consumer = MarketDataConsumer(manager, loop)

        consumer._run()

        mock_run_threadsafe.assert_called_once()
        args, _ = mock_run_threadsafe.call_args
        assert args[1] is loop

    @patch("market_data_api.consumer.asyncio.run_coroutine_threadsafe")
    @patch("market_data_api.consumer.create_consumer")
    def test_broadcast_payload_matches_the_event(
        self, mock_create, mock_run_threadsafe
    ):
        mock_create.return_value = [_msg(_VALID_EVENT)]
        manager = MagicMock()
        consumer = MarketDataConsumer(manager, MagicMock())

        consumer._run()

        manager.broadcast.assert_called_once()
        payload = manager.broadcast.call_args[0][0]
        assert payload["symbol"] == "AAPL"
        assert payload["best_bid"] == 175.0

    @patch("market_data_api.consumer.asyncio.run_coroutine_threadsafe")
    @patch("market_data_api.consumer.create_consumer")
    def test_malformed_message_is_skipped_not_raised(
        self, mock_create, mock_run_threadsafe
    ):
        mock_create.return_value = [_msg({"symbol": "AAPL"})]  # missing required fields
        manager = MagicMock()
        consumer = MarketDataConsumer(manager, MagicMock())

        consumer._run()  # must not raise

        manager.broadcast.assert_not_called()
        mock_run_threadsafe.assert_not_called()

    @patch("market_data_api.consumer.create_consumer")
    def test_one_bad_message_does_not_block_the_next_good_one(self, mock_create):
        mock_create.return_value = [
            _msg({"symbol": "AAPL"}),  # malformed
            _msg(_VALID_EVENT),
        ]
        manager = MagicMock()
        with patch("market_data_api.consumer.asyncio.run_coroutine_threadsafe"):
            consumer = MarketDataConsumer(manager, MagicMock())
            consumer._run()

        manager.broadcast.assert_called_once()


class TestStartStop:
    @patch("market_data_api.consumer.create_consumer")
    def test_stop_closes_consumer_and_joins_thread(self, mock_create):
        mock_consumer = MagicMock()
        mock_consumer.__iter__.return_value = iter([])  # thread exits immediately
        mock_create.return_value = mock_consumer
        consumer = MarketDataConsumer(MagicMock(), MagicMock())

        consumer.start()
        consumer.stop()

        mock_consumer.close.assert_called_once()
        assert consumer._thread is not None
        assert not consumer._thread.is_alive()
