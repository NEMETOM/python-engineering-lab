import logging
from .logging_config import generate_correlation_id

logger = logging.getLogger(__name__)


def apply_discount(price: float, discount_percent: float) -> float:
    correlation_id = generate_correlation_id()
    logger.info("Applying discount", extra={"correlation_id": correlation_id})

    if price < 0:
        logger.error("Negative price detected", extra={"correlation_id": correlation_id})
        raise ValueError("Price cannot be negative")

    if not 0 <= discount_percent <= 100:
        logger.error("Invalid discount percentage", extra={"correlation_id": correlation_id})
        raise ValueError("Discount must be between 0 and 100")

    result = price * (1 - discount_percent / 100)
    logger.info("Discount applied successfully", extra={"correlation_id": correlation_id})
    return result


def add_vat(price: float, vat_percent: float) -> float:
    correlation_id = generate_correlation_id()
    logger.info("Adding VAT", extra={"correlation_id": correlation_id})

    if vat_percent < 0:
        logger.error("Negative VAT detected", extra={"correlation_id": correlation_id})
        raise ValueError("VAT cannot be negative")

    result = price * (1 + vat_percent / 100)
    logger.info("VAT added successfully", extra={"correlation_id": correlation_id})
    return result
