import json
from unittest.mock import MagicMock, patch

from market_data_service.infrastructure.kafka_client import (
    create_consumer,
    create_producer,
)


def test_create_producer_returns_kafka_producer():
    with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
        mock_cls.return_value = MagicMock()
        producer = create_producer()
        assert producer is mock_cls.return_value
        mock_cls.assert_called_once()
        _, kwargs = mock_cls.call_args
        assert kwargs["bootstrap_servers"] == "localhost:9092"


def test_create_producer_serializer_encodes_json():
    with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
        mock_cls.return_value = MagicMock()
        create_producer()
        _, kwargs = mock_cls.call_args
        serializer = kwargs["value_serializer"]
        assert serializer({"price": 100}) == json.dumps({"price": 100}).encode()


def test_create_consumer_returns_kafka_consumer():
    with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
        mock_cls.return_value = MagicMock()
        consumer = create_consumer("trades", "market-data-service")
        assert consumer is mock_cls.return_value
        mock_cls.assert_called_once()
        args, kwargs = mock_cls.call_args
        assert args[0] == "trades"
        assert kwargs["bootstrap_servers"] == "localhost:9092"
        assert kwargs["group_id"] == "market-data-service"
        assert kwargs["auto_offset_reset"] == "earliest"


def test_create_consumer_deserializer_decodes_json():
    with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
        mock_cls.return_value = MagicMock()
        create_consumer("trades", "market-data-service")
        _, kwargs = mock_cls.call_args
        deserializer = kwargs["value_deserializer"]
        payload = {"symbol": "AAPL", "price": 150.0}
        assert deserializer(json.dumps(payload).encode()) == payload
