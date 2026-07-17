from order_service.infrastructure.kafka_client import create_consumer
from order_service.producer import Producer
from order_service.schemas import RawOrderEvent
from order_service.transformer import OrderTransformer
from order_service.utils.logger import configure_logging, get_logger
from order_service.validator import OrderValidator
from shared.observability.metrics import orders_processed
from shared.observability.tracing import extract_ctx, init_tracer

configure_logging()

logger = get_logger(__name__)

_tracer = init_tracer("order-service")


def run():

    consumer = create_consumer("raw_orders", "order-service")

    validator = OrderValidator()

    transformer = OrderTransformer()

    producer = Producer()

    for msg in consumer:

        ctx = extract_ctx(msg.value)

        with _tracer.start_as_current_span(
            "order-service.process", context=ctx
        ) as span:

            span.set_attribute("order.id", str(msg.value.get("order_id", "")))
            span.set_attribute("order.symbol", str(msg.value.get("symbol", "")))

            try:

                raw_event = RawOrderEvent(**msg.value)

                validator.validate(raw_event)

                validated = transformer.transform(raw_event)

                logger.info(f"validated order {validated}")

                producer.send(validated)

                orders_processed.labels(status="approved").inc()

            except Exception as e:

                span.record_exception(e)
                logger.error(f"invalid order {msg.value} reason={e}")
                orders_processed.labels(status="rejected").inc()


if __name__ == "__main__":

    run()
