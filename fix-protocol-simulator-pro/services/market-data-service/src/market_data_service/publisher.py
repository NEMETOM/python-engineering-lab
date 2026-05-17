from market_data_service.infrastructure.kafka_client import create_producer
from market_data_service.utils.logger import get_logger

logger = get_logger(__name__)


class MarketPublisher:

    def __init__(self, cache):

        self.cache = cache
        self.producer = create_producer()
        self._last_published = None

    def publish(self):

        snapshot = self.cache.snapshot()

        has_data = any(
            snapshot[k] is not None
            for k in ("best_bid", "best_ask", "last_trade_price")
        )

        if not has_data:
            logger.debug("no market data yet, skipping")
            return

        current_key = (snapshot["best_bid"], snapshot["best_ask"], snapshot["last_trade_price"])

        if current_key == self._last_published:
            logger.debug("market data unchanged, skipping")
            return

        logger.info(f"publishing market data {snapshot}")
        self.producer.send("market_data", snapshot)
        self._last_published = current_key
