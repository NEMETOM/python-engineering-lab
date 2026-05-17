from matching_engine.engine import MatchingEngine
from matching_engine.infrastructure.kafka_client import create_consumer
from matching_engine.models import Order
from matching_engine.order_book import OrderBook
from matching_engine.producer import Producer
from matching_engine.utils.logger import configure_logging, get_logger

configure_logging()

logger = get_logger(__name__)


def run():

    consumer = create_consumer("validated_orders", "matching-engine")

    book = OrderBook()

    engine = MatchingEngine(book)

    producer = Producer()

    for msg in consumer:

        event = msg.value

        logger.debug(f"received order {event}")

        order = Order(
            order_id=event["order_id"],
            side=event["side"],
            price=float(event["price"]),
            quantity=int(event["quantity"]),
            symbol=event.get("symbol", ""),
        )

        trades = engine.process(order)

        if trades:

            for trade in trades:

                logger.info(f"trade executed {trade}")

                producer.send_trade(trade)

            producer.send_book(book)


if __name__ == "__main__":

    run()
