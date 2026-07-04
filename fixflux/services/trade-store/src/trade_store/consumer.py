from trade_store.infrastructure.kafka_client import create_consumer
from trade_store.repository import TradeRepository
from trade_store.schemas import TradeEvent
from trade_store.utils.logger import configure_logging, get_logger
from shared.observability.tracing import extract_ctx, init_tracer

configure_logging()

logger = get_logger(__name__)

_tracer = init_tracer("trade-store")


def run():

    consumer = create_consumer("trades", "trade-store")

    repo = TradeRepository()

    for msg in consumer:

        ctx = extract_ctx(msg.value)

        with _tracer.start_as_current_span("trade-store.persist", context=ctx) as span:

            try:

                event = TradeEvent(**msg.value)

                span.set_attribute("trade.id", str(event.trade_id))

                logger.info(f"storing trade {event.trade_id}")

                repo.save(event)

            except Exception as e:

                span.record_exception(e)
                logger.error(f"failed to store trade {msg.value} reason={e}")


if __name__ == "__main__":  # pragma: no cover

    run()
