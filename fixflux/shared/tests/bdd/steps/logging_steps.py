import json
import logging

from behave import given, then, when
from shared.observability.formatters import JsonFormatter
from shared.observability.log_config import configure_logging, get_logger


@when('get_logger is called with name "{name}"')
def step_when_get_logger(context, name):
    context.logger = get_logger(name)


@then('a logger named "{name}" is returned')
def step_then_logger_named(context, name):
    assert isinstance(context.logger, logging.Logger)
    assert context.logger.name == name


@given("the root logger has no handlers")
def step_given_no_handlers(context):
    logging.getLogger().handlers.clear()


@when("configure_logging is called")
def step_when_configure_logging(context):
    configure_logging()


@when("configure_logging is called twice")
def step_when_configure_logging_twice(context):
    configure_logging()
    configure_logging()


@then("the root logger has at least one handler")
def step_then_has_handler(context):
    assert len(logging.getLogger().handlers) >= 1


@then("the root logger has exactly one handler")
def step_then_has_one_handler(context):
    assert len(logging.getLogger().handlers) == 1


@given('a log record with level "{level}" and message "{message}"')
def step_given_log_record(context, level, message):
    level_int = getattr(logging, level)
    context.record = logging.LogRecord(
        name="test",
        level=level_int,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )


@when("the JsonFormatter formats the record")
def step_when_json_formatter_formats(context):
    context.formatted = JsonFormatter().format(context.record)


@then("the output is valid JSON")
def step_then_valid_json(context):
    context.parsed = json.loads(context.formatted)
    assert isinstance(context.parsed, dict)


@then('the output field "{field}" equals "{value}"')
def step_then_field_equals(context, field, value):
    assert context.parsed[field] == value
