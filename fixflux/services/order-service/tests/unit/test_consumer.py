from datetime import datetime
from unittest.mock import MagicMock, patch


def _raw_msg_value(**overrides):
    defaults = dict(
        symbol="AAPL",
        side="BUY",
        price=100.0,
        quantity=10,
        timestamp=datetime.utcnow().isoformat(),
    )
    return {**defaults, **overrides}


class TestConsumerRun:
    @patch("order_service.consumer.Producer")
    @patch("order_service.consumer.create_consumer")
    def test_subscribes_to_raw_orders_topic(self, mock_create_consumer, _mock_producer):
        mock_create_consumer.return_value = iter([])
        from order_service.consumer import run

        run()
        mock_create_consumer.assert_called_once_with("raw_orders", "order-service")

    @patch("order_service.consumer.Producer")
    @patch("order_service.consumer.create_consumer")
    def test_no_messages_no_production(self, mock_create_consumer, mock_producer_cls):
        mock_create_consumer.return_value = iter([])
        mock_producer = MagicMock()
        mock_producer_cls.return_value = mock_producer
        from order_service.consumer import run

        run()
        mock_producer.send.assert_not_called()

    @patch("order_service.consumer.Producer")
    @patch("order_service.consumer.create_consumer")
    def test_valid_message_produces_validated_order(
        self, mock_create_consumer, mock_producer_cls
    ):
        msg = MagicMock()
        msg.value = _raw_msg_value()
        mock_create_consumer.return_value = iter([msg])
        mock_producer = MagicMock()
        mock_producer_cls.return_value = mock_producer
        from order_service.consumer import run

        run()
        mock_producer.send.assert_called_once()

    @patch("order_service.consumer.Producer")
    @patch("order_service.consumer.create_consumer")
    def test_invalid_price_logs_error_not_raises(
        self, mock_create_consumer, mock_producer_cls
    ):
        msg = MagicMock()
        msg.value = _raw_msg_value(price=-1.0)
        mock_create_consumer.return_value = iter([msg])
        mock_producer = MagicMock()
        mock_producer_cls.return_value = mock_producer
        from order_service.consumer import run

        run()
        mock_producer.send.assert_not_called()

    @patch("order_service.consumer.Producer")
    @patch("order_service.consumer.create_consumer")
    def test_multiple_valid_messages_each_produces(
        self, mock_create_consumer, mock_producer_cls
    ):
        msgs = [MagicMock(value=_raw_msg_value()) for _ in range(3)]
        mock_create_consumer.return_value = iter(msgs)
        mock_producer = MagicMock()
        mock_producer_cls.return_value = mock_producer
        from order_service.consumer import run

        run()
        assert mock_producer.send.call_count == 3
