from unittest.mock import MagicMock, patch


class TestConsumerRun:
    def test_subscribes_to_validated_orders_topic(self):
        with (
            patch("matching_engine.consumer.start_http_server"),
            patch("matching_engine.consumer.create_consumer") as mock_create,
            patch("matching_engine.consumer.Producer"),
        ):
            mock_create.return_value = []
            from matching_engine.consumer import run

            run()
            mock_create.assert_called_once_with("validated_orders", "matching-engine")

    def test_no_orders_no_trades_sent(self):
        with (
            patch("matching_engine.consumer.start_http_server"),
            patch("matching_engine.consumer.create_consumer") as mock_create,
            patch("matching_engine.consumer.Producer") as mock_producer_cls,
        ):
            mock_create.return_value = []
            mock_producer = MagicMock()
            mock_producer_cls.return_value = mock_producer
            from matching_engine.consumer import run

            run()
            mock_producer.send_trade.assert_not_called()

    def test_single_unmatched_order_does_not_send_book_snapshot(self):
        msg = MagicMock()
        msg.value = {
            "order_id": "B1",
            "symbol": "AAPL",
            "side": "BUY",
            "price": 100.0,
            "quantity": 10,
            "timestamp": "2026-01-01T00:00:00",
        }
        with (
            patch("matching_engine.consumer.start_http_server"),
            patch("matching_engine.consumer.create_consumer") as mock_create,
            patch("matching_engine.consumer.Producer") as mock_producer_cls,
        ):
            mock_create.return_value = [msg]
            mock_producer = MagicMock()
            mock_producer_cls.return_value = mock_producer
            from matching_engine.consumer import run

            run()
            mock_producer.send_book.assert_not_called()

    def test_matching_orders_produce_trade(self):
        buy_msg = MagicMock()
        buy_msg.value = {
            "order_id": "B1",
            "symbol": "AAPL",
            "side": "BUY",
            "price": 100.0,
            "quantity": 10,
            "timestamp": "2026-01-01T00:00:00",
        }
        sell_msg = MagicMock()
        sell_msg.value = {
            "order_id": "S1",
            "symbol": "AAPL",
            "side": "SELL",
            "price": 100.0,
            "quantity": 10,
            "timestamp": "2026-01-01T00:00:00",
        }
        with (
            patch("matching_engine.consumer.start_http_server"),
            patch("matching_engine.consumer.create_consumer") as mock_create,
            patch("matching_engine.consumer.Producer") as mock_producer_cls,
        ):
            mock_create.return_value = [buy_msg, sell_msg]
            mock_producer = MagicMock()
            mock_producer_cls.return_value = mock_producer
            from matching_engine.consumer import run

            run()
            mock_producer.send_trade.assert_called_once()
            mock_producer.send_book.assert_called_once()

    def test_unmatched_orders_do_not_send_book_snapshot(self):
        messages = [MagicMock() for _ in range(3)]
        for i, m in enumerate(messages):
            m.value = {
                "order_id": f"B{i}",
                "symbol": "AAPL",
                "side": "BUY",
                "price": 100.0 + i,
                "quantity": 5,
                "timestamp": "2026-01-01T00:00:00",
            }
        with (
            patch("matching_engine.consumer.start_http_server"),
            patch("matching_engine.consumer.create_consumer") as mock_create,
            patch("matching_engine.consumer.Producer") as mock_producer_cls,
        ):
            mock_create.return_value = messages
            mock_producer = MagicMock()
            mock_producer_cls.return_value = mock_producer
            from matching_engine.consumer import run

            run()
            mock_producer.send_book.assert_not_called()
