# src/event_stream_risk_detector/logger.py

import logging
import sys


def setup_logger(
    name: str = "event_stream_risk_detector",
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


logger: logging.Logger = setup_logger()
