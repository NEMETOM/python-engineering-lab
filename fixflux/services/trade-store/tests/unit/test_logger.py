import logging

from trade_store.utils.logger import configure_logging, get_logger


class TestConfigureLogging:
    def test_configure_logging_runs_without_error(self):
        configure_logging()  # must not raise

    def test_configure_logging_sets_info_level(self):
        root = logging.getLogger()
        root.handlers.clear()  # basicConfig is a no-op when handlers already exist
        configure_logging()
        assert root.level <= logging.INFO


class TestGetLogger:
    def test_returns_logger_instance(self):
        logger = get_logger("trade_store.test")
        assert isinstance(logger, logging.Logger)

    def test_logger_name_matches(self):
        logger = get_logger("trade_store.consumer")
        assert logger.name == "trade_store.consumer"

    def test_different_names_return_different_loggers(self):
        a = get_logger("trade_store.a")
        b = get_logger("trade_store.b")
        assert a is not b

    def test_same_name_returns_same_logger(self):
        a = get_logger("trade_store.shared")
        b = get_logger("trade_store.shared")
        assert a is b
