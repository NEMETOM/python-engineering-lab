import json
from unittest.mock import MagicMock, patch

from matching_engine.infrastructure.kafka_client import create_consumer, create_producer


class TestCreateProducer:
    def test_returns_kafka_producer_instance(self):
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            assert create_producer() == mock_instance

    def test_connects_to_kafka_broker(self):
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            create_producer()
            assert mock_cls.call_args[1]["bootstrap_servers"] == "localhost:9092"

    def test_value_serializer_encodes_dict_as_json_bytes(self):
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            create_producer()
            serializer = mock_cls.call_args[1]["value_serializer"]
            result = serializer({"key": "value"})
            assert result == b'{"key": "value"}'

    def test_value_serializer_handles_nested_data(self):
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            create_producer()
            serializer = mock_cls.call_args[1]["value_serializer"]
            data = {"price": 100.0, "quantity": 10}
            decoded = json.loads(serializer(data))
            assert decoded == data


class TestCreateConsumer:
    def test_returns_kafka_consumer_instance(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            assert create_consumer("test_topic", "test_group") == mock_instance

    def test_subscribes_to_given_topic(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("validated_orders", "matching-engine")
            assert mock_cls.call_args[0][0] == "validated_orders"

    def test_uses_given_group_id(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("validated_orders", "matching-engine")
            assert mock_cls.call_args[1]["group_id"] == "matching-engine"

    def test_connects_to_kafka_broker(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("validated_orders", "matching-engine")
            assert mock_cls.call_args[1]["bootstrap_servers"] == "localhost:9092"

    def test_offset_reset_is_earliest(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("validated_orders", "matching-engine")
            assert mock_cls.call_args[1]["auto_offset_reset"] == "earliest"

    def test_value_deserializer_decodes_json_bytes(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            create_consumer("validated_orders", "matching-engine")
            deserializer = mock_cls.call_args[1]["value_deserializer"]
            result = deserializer(b'{"order_id": "O1", "price": 100.0}')
            assert result == {"order_id": "O1", "price": 100.0}
