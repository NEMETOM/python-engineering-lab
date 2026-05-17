import json
from unittest.mock import patch

from order_service.infrastructure.kafka_client import create_consumer, create_producer


class TestCreateProducer:
    @patch("shared.infrastructure.kafka_client.KafkaProducer")
    def test_returns_kafka_producer_instance(self, mock_cls):
        result = create_producer()
        assert result is mock_cls.return_value

    @patch("shared.infrastructure.kafka_client.KafkaProducer")
    def test_connects_to_kafka_broker(self, mock_cls):
        create_producer()
        _, kwargs = mock_cls.call_args
        assert "bootstrap_servers" in kwargs

    @patch("shared.infrastructure.kafka_client.KafkaProducer")
    def test_value_serializer_encodes_dict_as_json_bytes(self, mock_cls):
        create_producer()
        _, kwargs = mock_cls.call_args
        serializer = kwargs["value_serializer"]
        assert serializer({"key": "val"}) == json.dumps({"key": "val"}).encode()

    @patch("shared.infrastructure.kafka_client.KafkaProducer")
    def test_value_serializer_handles_nested_data(self, mock_cls):
        create_producer()
        _, kwargs = mock_cls.call_args
        serializer = kwargs["value_serializer"]
        payload = {"a": {"b": 1}}
        assert serializer(payload) == json.dumps(payload).encode()


class TestCreateConsumer:
    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_returns_kafka_consumer_instance(self, mock_cls):
        result = create_consumer("raw_orders", "order-service")
        assert result is mock_cls.return_value

    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_subscribes_to_given_topic(self, mock_cls):
        create_consumer("raw_orders", "order-service")
        args, _ = mock_cls.call_args
        assert "raw_orders" in args

    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_uses_given_group_id(self, mock_cls):
        create_consumer("raw_orders", "order-service")
        _, kwargs = mock_cls.call_args
        assert kwargs["group_id"] == "order-service"

    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_connects_to_kafka_broker(self, mock_cls):
        create_consumer("raw_orders", "order-service")
        _, kwargs = mock_cls.call_args
        assert "bootstrap_servers" in kwargs

    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_offset_reset_is_earliest(self, mock_cls):
        create_consumer("raw_orders", "order-service")
        _, kwargs = mock_cls.call_args
        assert kwargs["auto_offset_reset"] == "earliest"

    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_value_deserializer_decodes_json_bytes(self, mock_cls):
        create_consumer("raw_orders", "order-service")
        _, kwargs = mock_cls.call_args
        deserializer = kwargs["value_deserializer"]
        payload = {"symbol": "AAPL"}
        assert deserializer(json.dumps(payload).encode()) == payload
