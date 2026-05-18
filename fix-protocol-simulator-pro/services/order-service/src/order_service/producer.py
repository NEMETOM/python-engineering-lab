from order_service.infrastructure.kafka_client import create_producer


class Producer:

    def __init__(self):

        self.producer = create_producer()

    def send(self, event):

        self.producer.send("validated_orders", event.model_dump(mode="json"))
