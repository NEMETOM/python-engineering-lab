import json
from kafka import KafkaConsumer

from event_stream_risk_detector.risk_evaluator import evaluate_transaction
from event_stream_risk_detector.logging_config import get_logger

logger = get_logger(__name__)


def run_consumer():
    consumer = KafkaConsumer(
        "transactions",
        bootstrap_servers="localhost:9092",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="risk-detector-group",
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )

    logger.info("Consumer started")

    for message in consumer:
        transaction = message.value

        logger.info(
            "Received transaction",
            extra={"extra_data": transaction},
        )

        result = evaluate_transaction(transaction)

        logger.info(
            "Risk evaluation completed",
            extra={"extra_data": result},
        )
