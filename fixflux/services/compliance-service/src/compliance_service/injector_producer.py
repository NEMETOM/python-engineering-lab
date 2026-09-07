import os

from shared.infrastructure.kafka_client import create_producer

TARGET_TOPIC = os.getenv("FIX_INJECTOR_TARGET_TOPIC", "raw_orders")


class InjectorProducer:
    def __init__(self):
        self._producer = create_producer()

    def send(self, event: dict) -> None:
        self._producer.send(TARGET_TOPIC, event)

    def flush(self) -> None:
        self._producer.flush()
