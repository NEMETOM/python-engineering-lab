from datetime import datetime
from unittest.mock import MagicMock, patch

from order_service.producer import Producer
from order_service.schemas import ValidatedOrderEvent


def _make_validated(**overrides):
    defaults = dict(
        order_id="test-uuid",
        symbol="AAPL",
        side="BUY",
        price=100.0,
        quantity=10,
        timestamp=datetime.utcnow(),
    )
    return ValidatedOrderEvent(**{**defaults, **overrides})


class TestProducerSend:
    @patch("order_service.producer.create_producer")
    def test_sends_to_validated_orders_topic(self, mock_create_producer):
        mock_kafka = MagicMock()
        mock_create_producer.return_value = mock_kafka
        producer = Producer()
        producer.send(_make_validated())
        args, _ = mock_kafka.send.call_args
        assert args[0] == "validated_orders"

    @patch("order_service.producer.create_producer")
    def test_sends_model_dump_as_payload(self, mock_create_producer):
        mock_kafka = MagicMock()
        mock_create_producer.return_value = mock_kafka
        producer = Producer()
        event = _make_validated()
        producer.send(event)
        args, _ = mock_kafka.send.call_args
        assert args[1] == event.model_dump(mode="json")

    @patch("order_service.producer.create_producer")
    def test_send_called_once(self, mock_create_producer):
        mock_kafka = MagicMock()
        mock_create_producer.return_value = mock_kafka
        producer = Producer()
        producer.send(_make_validated())
        assert mock_kafka.send.call_count == 1
