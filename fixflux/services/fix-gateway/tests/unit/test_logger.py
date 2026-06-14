# fixflux/services/fix-gateway/tests/unit/test_logger.py

import logging

from fix_gateway.utils.logger import configure_logging, get_logger


def test_get_logger_returns_logger():

    logger = get_logger("test.module")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_configure_logging_runs_without_error():

    configure_logging()  # should not raise
