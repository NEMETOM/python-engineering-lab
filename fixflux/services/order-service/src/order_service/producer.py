from order_service.infrastructure.kafka_client import create_producer
from shared.observability.tracing import inject_ctx


class Producer:

    def __init__(self):

        self.producer = create_producer()

    def send(self, event):

        data = event.model_dump(mode="json")
        inject_ctx(data)
        self.producer.send("validated_orders", data)
