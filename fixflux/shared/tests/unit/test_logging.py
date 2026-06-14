import logging
from unittest.mock import patch

from shared.observability.formatters import JsonFormatter
from shared.observability.log_config import configure_logging, get_logger


class TestGetLogger:
    def test_returns_logger_instance(self):
        assert isinstance(get_logger("test.module"), logging.Logger)

    def test_logger_name_matches(self):
        assert get_logger("order_service").name == "order_service"

    def test_different_names_return_different_loggers(self):
        l1 = get_logger("service.a")
        l2 = get_logger("service.b")
        assert l1.name != l2.name

    def test_same_name_returns_same_logger(self):
        assert get_logger("shared.x") is get_logger("shared.x")


class TestConfigureLogging:
    def _clear_and_restore(self):
        root = logging.getLogger()
        saved = root.handlers[:]
        root.handlers.clear()
        return root, saved

    def test_adds_handler_to_root_logger(self):
        root, saved = self._clear_and_restore()
        try:
            configure_logging()
            assert len(root.handlers) >= 1
        finally:
            root.handlers.clear()
            root.handlers.extend(saved)

    def test_is_idempotent(self):
        root, saved = self._clear_and_restore()
        try:
            configure_logging()
            count = len(root.handlers)
            configure_logging()
            assert len(root.handlers) == count
        finally:
            root.handlers.clear()
            root.handlers.extend(saved)

    def test_uses_json_formatter_when_log_format_is_json(self):
        root, saved = self._clear_and_restore()
        try:
            with patch("shared.observability.log_config.LOG_FORMAT", "json"):
                configure_logging()
            assert any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)
        finally:
            root.handlers.clear()
            root.handlers.extend(saved)

    def test_uses_plain_formatter_by_default(self):
        root, saved = self._clear_and_restore()
        try:
            with patch("shared.observability.log_config.LOG_FORMAT", "plain"):
                configure_logging()
            assert not all(
                isinstance(h.formatter, JsonFormatter) for h in root.handlers
            )
        finally:
            root.handlers.clear()
            root.handlers.extend(saved)
