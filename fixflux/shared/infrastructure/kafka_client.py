import json
import os

from kafka import KafkaConsumer, KafkaProducer, TopicPartition

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")


def create_producer():
    # enable_idempotence defaults to True in kafka-python. Idle producers (this
    # process can sit for days between orders) have their producer ID expired
    # broker-side; the first send afterwards raises OutOfOrderSequenceNumberError,
    # which the client "recovers" from by bumping the epoch and dropping that
    # send - silently, since .send() here is fire-and-forget. These topics are
    # already at-least-once, not exactly-once, so idempotence buys nothing and
    # costs silent message loss.
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        enable_idempotence=False,
    )


def create_exec_report_producer():
    # Short max_block_ms so a missing execution_reports topic never stalls
    # the calling thread (and therefore the consumer loop) for 60 seconds.
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        max_block_ms=1_000,
        enable_idempotence=False,
    )


def create_consumer(topic: str, group_id: str):

    return KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BROKER,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )


def create_tail_consumer(topic: str):
    # Groupless reader positioned at the current end of every partition, for
    # short-lived tools (fix-replay) that only care about messages produced
    # after they start. No group_id means no committed offsets: a consumer
    # group left behind by a one-off run would show ever-growing lag in
    # kafka-exporter and eventually fire KafkaConsumerLagHigh.
    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BROKER,
        group_id=None,
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    partitions = consumer.partitions_for_topic(topic) or set()
    if not partitions:
        consumer.close()
        raise RuntimeError(f"topic {topic!r} does not exist or has no partitions")
    assignment = [TopicPartition(topic, p) for p in sorted(partitions)]
    consumer.assign(assignment)
    consumer.seek_to_end(*assignment)
    # seek_to_end is lazy; position() resolves it now, before anything is
    # produced, so messages sent after this call can't be skipped.
    for tp in assignment:
        consumer.position(tp)
    return consumer
