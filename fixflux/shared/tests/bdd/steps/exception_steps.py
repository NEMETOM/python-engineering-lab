from behave import given, then
from shared.exceptions import AppException, InfrastructureError, ValidationError

_EXCEPTION_MAP = {
    "ValidationError": ValidationError,
    "InfrastructureError": InfrastructureError,
    "AppException": AppException,
}


@given('an AppException is raised with message "{message}"')
def step_given_app_exception(context, message):
    context.exc = None
    try:
        raise AppException(message)
    except AppException as e:
        context.exc = e


@given('a ValidationError is raised with message "{message}"')
def step_given_validation_error(context, message):
    context.exc = None
    try:
        raise ValidationError(message)
    except ValidationError as e:
        context.exc = e


@given('an InfrastructureError is raised with message "{message}"')
def step_given_infrastructure_error(context, message):
    context.exc = None
    try:
        raise InfrastructureError(message)
    except InfrastructureError as e:
        context.exc = e


@given('a {exception_type} is raised with message "{message}"')
def step_given_typed_exception(context, exception_type, message):
    cls = _EXCEPTION_MAP[exception_type]
    context.exc = None
    try:
        raise cls(message)
    except cls as e:
        context.exc = e


@then('the exception message is "{message}"')
def step_then_exception_message(context, message):
    assert str(context.exc) == message


@then("it is an instance of Exception")
def step_then_is_exception(context):
    assert isinstance(context.exc, Exception)


@then("the exception is an instance of AppException")
def step_then_is_app_exception(context):
    assert isinstance(context.exc, AppException)


@then("catching AppException succeeds")
def step_then_caught_as_app_exception(context):
    assert isinstance(context.exc, AppException)
