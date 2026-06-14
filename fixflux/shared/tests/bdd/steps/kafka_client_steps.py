import json
from unittest.mock import patch

from behave import then, when


@when("create_producer is called")
def step_when_create_producer(context):
    with patch("shared.infrastructure.kafka_client.KafkaProducer") as mock_cls:
        from shared.infrastructure.kafka_client import create_producer

        create_producer()
        context.producer_args = mock_cls.call_args


@then('the producer bootstrap_servers is "{broker}"')
def step_then_producer_broker(context, broker):
    _, kwargs = context.producer_args
    assert kwargs["bootstrap_servers"] == broker


@then('the producer value_serializer encodes "{key}" as JSON bytes')
def step_then_producer_serializer(context, key):
    _, kwargs = context.producer_args
    serializer = kwargs["value_serializer"]
    data = {key: "value"}
    assert serializer(data) == json.dumps(data).encode()


@when('create_consumer is called with topic "{topic}" and group "{group}"')
def step_when_create_consumer(context, topic, group):
    with patch("shared.infrastructure.kafka_client.KafkaConsumer") as mock_cls:
        from shared.infrastructure.kafka_client import create_consumer

        create_consumer(topic, group)
        context.consumer_args = mock_cls.call_args
        context.consumer_topic = topic
        context.consumer_group = group


@then('the consumer subscribes to topic "{topic}"')
def step_then_consumer_topic(context, topic):
    args, _ = context.consumer_args
    assert args[0] == topic


@then('the consumer group_id is "{group}"')
def step_then_consumer_group(context, group):
    _, kwargs = context.consumer_args
    assert kwargs["group_id"] == group


@then('the consumer auto_offset_reset is "{value}"')
def step_then_consumer_offset_reset(context, value):
    _, kwargs = context.consumer_args
    assert kwargs["auto_offset_reset"] == value


@then('the consumer deserializer decodes "{payload}" correctly')
def step_then_consumer_deserializer(context, payload):
    _, kwargs = context.consumer_args
    deserializer = kwargs["value_deserializer"]
    expected = json.loads(payload)
    assert deserializer(payload.encode()) == expected
