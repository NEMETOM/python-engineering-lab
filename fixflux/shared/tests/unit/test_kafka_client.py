import json
from unittest.mock import patch

import pytest
from kafka import TopicPartition

from shared.infrastructure.kafka_client import (
    create_consumer,
    create_exec_report_producer,
    create_producer,
    create_tail_consumer,
)


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


class TestCreateTailConsumer:
    def _mock(self, mock_cls, partitions):
        consumer = mock_cls.return_value
        consumer.partitions_for_topic.return_value = partitions
        return consumer

    def test_returns_kafka_consumer(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            consumer = self._mock(mock_cls, {0})
            assert create_tail_consumer("execution_reports") is consumer

    def test_has_no_group_and_never_commits(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            self._mock(mock_cls, {0})
            create_tail_consumer("execution_reports")
            _, kwargs = mock_cls.call_args
            assert kwargs["group_id"] is None
            assert kwargs["enable_auto_commit"] is False

    def test_assigns_every_partition_and_seeks_to_end(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            consumer = self._mock(mock_cls, {1, 0})
            create_tail_consumer("execution_reports")
            expected = [
                TopicPartition("execution_reports", 0),
                TopicPartition("execution_reports", 1),
            ]
            consumer.assign.assert_called_once_with(expected)
            consumer.seek_to_end.assert_called_once_with(*expected)
            assert consumer.position.call_count == 2

    def test_missing_topic_raises_and_closes(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            consumer = self._mock(mock_cls, None)
            with pytest.raises(RuntimeError, match="does not exist"):
                create_tail_consumer("nope")
            consumer.close.assert_called_once()

    def test_deserializer_decodes_json_bytes(self):
        with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
            self._mock(mock_cls, {0})
            create_tail_consumer("execution_reports")
            _, kwargs = mock_cls.call_args
            assert kwargs["value_deserializer"](b'{"a": 1}') == {"a": 1}


class TestCreateExecReportProducer:
    def test_short_max_block_so_a_missing_topic_cannot_stall_the_consumer(self):
        # A missing execution_reports topic used to block the calling consumer
        # loop for kafka-python's 60s default; 1s bounds the damage.
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            create_exec_report_producer()
            _, kwargs = mock_cls.call_args
            assert kwargs["max_block_ms"] == 1_000

    def test_idempotence_disabled_like_every_other_producer(self):
        # Idle idempotent producers silently dropped their first message after
        # a long gap (OutOfOrderSequenceNumberError) - see create_producer.
        with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
            create_exec_report_producer()
            _, kwargs = mock_cls.call_args
            assert kwargs["enable_idempotence"] is False
