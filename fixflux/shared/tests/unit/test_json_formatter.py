import json
import logging

from shared.observability.formatters import JsonFormatter


def _make_record(level=logging.INFO, message="test message", name="test_logger"):
    return logging.LogRecord(
        name=name,
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )


class TestJsonFormatter:
    def test_format_returns_valid_json(self):
        output = JsonFormatter().format(_make_record())
        assert isinstance(json.loads(output), dict)

    def test_format_includes_level(self):
        parsed = json.loads(JsonFormatter().format(_make_record(level=logging.ERROR)))
        assert parsed["level"] == "ERROR"

    def test_format_includes_message(self):
        parsed = json.loads(
            JsonFormatter().format(_make_record(message="order received"))
        )
        assert parsed["message"] == "order received"

    def test_format_includes_logger_name(self):
        parsed = json.loads(JsonFormatter().format(_make_record(name="order.service")))
        assert parsed["logger"] == "order.service"

    def test_format_includes_timestamp(self):
        parsed = json.loads(JsonFormatter().format(_make_record()))
        assert "timestamp" in parsed

    def test_format_includes_service_field(self):
        parsed = json.loads(JsonFormatter().format(_make_record()))
        assert "service" in parsed

    def test_format_warning_level(self):
        parsed = json.loads(JsonFormatter().format(_make_record(level=logging.WARNING)))
        assert parsed["level"] == "WARNING"

    def test_format_info_level(self):
        parsed = json.loads(JsonFormatter().format(_make_record(level=logging.INFO)))
        assert parsed["level"] == "INFO"
