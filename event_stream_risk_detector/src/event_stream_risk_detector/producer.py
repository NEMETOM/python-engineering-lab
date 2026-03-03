# event_stream_risk_detector/src/event_stream_risk_detector/producer.py

import json

from kafka import KafkaProducer
from kafka.errors import KafkaError

from event_stream_risk_detector.logging_config import (generate_correlation_id,
                                                       get_logger)

logger = get_logger(__name__)


class TransactionProducer:
    """Kafka producer wrapper for sending transactions."""

    def __init__(self, bootstrap_servers: str, topic: str):
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=3,
        )
        logger.info(
            "Kafka producer initialized",
            extra={
                "extra_data": {"bootstrap_servers": bootstrap_servers, "topic": topic}
            },
        )

    def send_transaction(self, transaction: dict) -> None:
        correlation_id = generate_correlation_id()
        try:
            future = self.producer.send(self.topic, transaction)
            record_metadata = future.get(timeout=10)

            logger.info(
                "Transaction sent",
                extra={
                    "correlation_id": correlation_id,
                    "extra_data": {
                        "transaction": transaction,
                        "topic": record_metadata.topic,
                        "partition": record_metadata.partition,
                        "offset": record_metadata.offset,
                    },
                },
            )

        except KafkaError as e:
            logger.exception(
                "Failed to send transaction",
                extra={
                    "correlation_id": correlation_id,
                    "extra_data": {"transaction": transaction},
                },
            )
            raise

    def close(self):
        self.producer.flush()
        self.producer.close()
        logger.info("Kafka producer closed")


# ------------------------
# CLI ENTRYPOINT
# ------------------------
def main():
    producer = TransactionProducer(
        bootstrap_servers="localhost:9092",
        topic="transactions",
    )

    # Example transaction
    transaction = {
        "transaction_id": "tx-123",
        "user_id": "user-42",
        "amount": 2500,
        "currency": "GBP",
    }

    producer.send_transaction(transaction)
    producer.close()


if __name__ == "__main__":
    main()
