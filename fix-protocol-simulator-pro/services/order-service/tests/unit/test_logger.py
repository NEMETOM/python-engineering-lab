import logging

from order_service.utils.logger import configure_logging, get_logger


class TestConfigureLogging:
    def test_does_not_raise(self):
        configure_logging()

    def test_callable_multiple_times_without_error(self):
        configure_logging()
        configure_logging()


class TestGetLogger:
    def test_returns_logger_instance(self):
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name(self):
        logger = get_logger("test.module")
        assert logger.name == "test.module"
