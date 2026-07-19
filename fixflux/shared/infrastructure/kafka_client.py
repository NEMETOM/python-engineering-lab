import json
import os

from kafka import KafkaConsumer, KafkaProducer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")


def create_producer():

    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def create_exec_report_producer():
    # Short max_block_ms so a missing execution_reports topic never stalls
    # the calling thread (and therefore the consumer loop) for 60 seconds.
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        max_block_ms=1_000,
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
