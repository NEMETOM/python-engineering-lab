import time

from prometheus_client import start_http_server

from matching_engine.engine import MatchingEngine
from matching_engine.infrastructure.kafka_client import create_consumer
from matching_engine.models import Order
from matching_engine.order_book import OrderBook
from matching_engine.producer import Producer
from matching_engine.utils.logger import configure_logging, get_logger
from shared.observability.metrics import (
    kafka_messages_consumed,
    order_matching_latency,
    orders_in_book,
    trades_executed,
)

configure_logging()

logger = get_logger(__name__)

_METRICS_PORT = 8003


def run():
    start_http_server(_METRICS_PORT)
    logger.info(f"metrics server started on :{_METRICS_PORT}")
    consumer = create_consumer("risk_approved_orders", "matching-engine")
    book = OrderBook()
    engine = MatchingEngine(book)
    producer = Producer()
    for msg in consumer:
        kafka_messages_consumed.labels(
            topic="risk_approved_orders", service="matching-engine"
        ).inc()
        event = msg.value
        logger.debug(f"received order {event}")
        order = Order(
            order_id=event["order_id"],
            side=event["side"],
            price=float(event["price"]),
            quantity=int(event["quantity"]),
            symbol=event.get("symbol", ""),
        )
        t0 = time.perf_counter()
        trades = engine.process(order)
        order_matching_latency.observe(time.perf_counter() - t0)
        orders_in_book.labels(side="buy").set(len(book.buys))
        orders_in_book.labels(side="sell").set(len(book.sells))
        if trades:
            for trade in trades:
                logger.info(f"trade executed {trade}")
                trades_executed.labels(symbol=trade.symbol).inc()
                producer.send_trade(trade)
            producer.send_book(book)


if __name__ == "__main__":
    run()
