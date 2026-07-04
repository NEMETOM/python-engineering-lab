from matching_engine.infrastructure.kafka_client import create_producer
from shared.observability.tracing import inject_ctx


class Producer:

    def __init__(self):

        self.producer = create_producer()

    def send_trade(self, trade):

        data = {**trade.__dict__}
        inject_ctx(data)
        self.producer.send("trades", data)

    def send_book(self, book):

        snapshot = {
            "best_bid": book.best_bid().price if book.best_bid() else None,
            "best_ask": book.best_ask().price if book.best_ask() else None,
        }

        self.producer.send("order_book_updates", snapshot)
