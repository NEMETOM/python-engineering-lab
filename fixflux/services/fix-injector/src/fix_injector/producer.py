from fix_injector.config import settings
from shared.infrastructure.kafka_client import create_producer


class InjectorProducer:
    def __init__(self):
        self._producer = create_producer()

    def send(self, event: dict) -> None:
        self._producer.send(settings.target_topic, event)

    def flush(self) -> None:
        self._producer.flush()
