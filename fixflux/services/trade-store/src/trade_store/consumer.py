from trade_store.infrastructure.kafka_client import create_consumer
from trade_store.repository import TradeRepository
from trade_store.schemas import TradeEvent
from trade_store.utils.logger import configure_logging, get_logger

configure_logging()

logger = get_logger(__name__)


def run():

    consumer = create_consumer("trades", "trade-store")

    repo = TradeRepository()

    for msg in consumer:

        try:

            event = TradeEvent(**msg.value)

            logger.info(f"storing trade {event.trade_id}")

            repo.save(event)

        except Exception as e:

            logger.error(f"failed to store trade {msg.value} reason={e}")


if __name__ == "__main__":  # pragma: no cover

    run()
