from event_stream_risk_detector.logging_config import (
    generate_correlation_id,
    get_logger,
)

logger = get_logger(__name__)


def evaluate_transaction(transaction: dict) -> dict:
    correlation_id = generate_correlation_id()

    amount = transaction.get("amount", 0)
    high_value = amount > 10000

    logger.info(
        "Evaluating transaction",
        extra={
            "correlation_id": correlation_id,
            "extra_data": {
                "transaction_id": transaction.get("transaction_id"),
                "user_id": transaction.get("user_id"),
                "amount": amount,
                "high_value": high_value,
            },
        },
    )

    return {
        "transaction_id": transaction.get("transaction_id"),
        "high_value": high_value,
        "correlation_id": correlation_id,
    }
