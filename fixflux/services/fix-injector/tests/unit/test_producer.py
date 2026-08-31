from unittest.mock import MagicMock, patch

from fix_injector.producer import InjectorProducer


@patch("shared.infrastructure.kafka_client.KafkaProducer")
def test_send_publishes_to_configured_target_topic(mock_cls):
    mock_cls.return_value = MagicMock()

    producer = InjectorProducer()
    producer.send({"symbol": "EURUSD"})

    mock_cls.return_value.send.assert_called_once_with(
        "raw_orders", {"symbol": "EURUSD"}
    )


@patch("shared.infrastructure.kafka_client.KafkaProducer")
def test_flush_delegates_to_underlying_producer(mock_cls):
    mock_cls.return_value = MagicMock()

    producer = InjectorProducer()
    producer.flush()

    mock_cls.return_value.flush.assert_called_once()
