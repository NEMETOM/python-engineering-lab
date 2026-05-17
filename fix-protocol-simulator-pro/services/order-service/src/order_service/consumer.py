from order_service.infrastructure.kafka_client import create_consumer
from order_service.producer import Producer
from order_service.schemas import RawOrderEvent
from order_service.transformer import OrderTransformer
from order_service.utils.logger import configure_logging, get_logger
from order_service.validator import OrderValidator

configure_logging()

logger = get_logger(__name__)


def run():

    consumer = create_consumer("raw_orders", "order-service")

    validator = OrderValidator()

    transformer = OrderTransformer()

    producer = Producer()

    for msg in consumer:

        try:

            raw_event = RawOrderEvent(**msg.value)

            validator.validate(raw_event)

            validated = transformer.transform(raw_event)

            logger.info(f"validated order {validated}")

            producer.send(validated)

        except Exception as e:

            logger.error(f"invalid order {msg.value} reason={e}")


if __name__ == "__main__":

    run()
