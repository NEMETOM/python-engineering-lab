from risk_service import config
from shared.infrastructure.kafka_client import create_producer
from shared.observability.tracing import inject_ctx


class RiskProducer:

    def __init__(self):
        self._producer = create_producer()

    def approve(self, order_dict: dict) -> None:
        data = {**order_dict}
        inject_ctx(data)
        self._producer.send(config.APPROVED_TOPIC, data)

    def reject(self, rejection_dict: dict) -> None:
        data = {**rejection_dict}
        inject_ctx(data)
        self._producer.send(config.REJECTED_TOPIC, data)
