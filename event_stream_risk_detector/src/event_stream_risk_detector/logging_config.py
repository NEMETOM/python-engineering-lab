# event_stream_risk_detector/src/event_stream_risk_detector/logging_config.py

import logging
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict

# Set log level from environment variable, default to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "event-stream-risk-detector",
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Optional fields
        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id
        if hasattr(record, "extra_data"):
            log_record.update(record.extra_data)

        return json.dumps(log_record)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance with JSON formatting.
    Ensures multiple calls return the same logger with a single handler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False  # Prevent double logging in root logger

    return logger


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for tracing logs across services."""
    return str(uuid.uuid4())