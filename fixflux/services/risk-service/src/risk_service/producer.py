from risk_service import config
from shared.infrastructure.kafka_client import create_producer


class RiskProducer:

    def __init__(self):
        self._producer = create_producer()

    def approve(self, order_dict: dict) -> None:
        self._producer.send(config.APPROVED_TOPIC, order_dict)

    def reject(self, rejection_dict: dict) -> None:
        self._producer.send(config.REJECTED_TOPIC, rejection_dict)
