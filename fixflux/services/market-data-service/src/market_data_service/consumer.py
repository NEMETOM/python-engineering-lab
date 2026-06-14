from market_data_service.infrastructure.kafka_client import create_consumer
from market_data_service.market_cache import MarketCache
from market_data_service.publisher import MarketPublisher
from market_data_service.utils.logger import configure_logging, get_logger

configure_logging()

logger = get_logger(__name__)


def run():

    book_consumer = create_consumer("order_book_updates", "market-data-service")
    trade_consumer = create_consumer("trades", "market-data-service")

    cache = MarketCache()
    publisher = MarketPublisher(cache)

    while True:

        updated = False

        for records in book_consumer.poll(timeout_ms=100).values():
            for msg in records:
                cache.update_order_book(msg.value)
                updated = True

        for records in trade_consumer.poll(timeout_ms=100).values():
            for msg in records:
                cache.update_trade(msg.value)
                updated = True

        if updated:
            publisher.publish()


if __name__ == "__main__":  # pragma: no cover

    run()
