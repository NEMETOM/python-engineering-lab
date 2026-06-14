import logging
import os
import sys

from .formatters import JsonFormatter

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "plain")  # plain | json


def configure_logging():
    if logging.getLogger().handlers:
        return

    handler = logging.StreamHandler(sys.stdout)

    if LOG_FORMAT == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    root_logger.addHandler(handler)


def get_logger(name: str):
    return logging.getLogger(name)
