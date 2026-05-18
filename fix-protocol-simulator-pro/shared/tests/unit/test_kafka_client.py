import json
from unittest.mock import patch

from shared.infrastructure.kafka_client import create_consumer, create_producer


class TestCreateProducer:
    def test_returns_kafka_producer(self):
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            result = create_producer()
            assert result is mock_cls.return_value

    def test_uses_configured_broker(self):
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            create_producer()
            _, kwargs = mock_cls.call_args
            assert kwargs["bootstrap_servers"] == "localhost:9092"

    def test_serializer_encodes_dict_as_json_bytes(self):
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            create_producer()
            _, kwargs = mock_cls.call_args
            serializer = kwargs["value_serializer"]
            assert serializer({"key": "val"}) == b'{"key": "val"}'

    def test_serializer_handles_nested_data(self):
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            create_producer()
            _, kwargs = mock_cls.call_args
            serializer = kwargs["value_serializer"]
            data = {"price": 100.0, "meta": {"symbol": "AAPL"}}
            assert serializer(data) == json.dumps(data).encode()


class TestCreateConsumer:
    def test_returns_kafka_consumer(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            result = create_consumer("topic", "group")
            assert result is mock_cls.return_value

    def test_subscribes_to_given_topic(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("validated_orders", "matching-engine")
            args, _ = mock_cls.call_args
            assert args[0] == "validated_orders"

    def test_uses_given_group_id(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("validated_orders", "matching-engine")
            _, kwargs = mock_cls.call_args
            assert kwargs["group_id"] == "matching-engine"

    def test_connects_to_configured_broker(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("topic", "group")
            _, kwargs = mock_cls.call_args
            assert kwargs["bootstrap_servers"] == "localhost:9092"

    def test_auto_offset_reset_is_earliest(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("topic", "group")
            _, kwargs = mock_cls.call_args
            assert kwargs["auto_offset_reset"] == "earliest"

    def test_deserializer_decodes_json_bytes(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("topic", "group")
            _, kwargs = mock_cls.call_args
            deserializer = kwargs["value_deserializer"]
            payload = {"order_id": "O1", "price": 100.0}
            assert deserializer(json.dumps(payload).encode()) == payload
