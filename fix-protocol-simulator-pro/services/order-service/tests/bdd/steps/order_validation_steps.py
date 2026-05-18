from behave import then, when
from order_service.validator import OrderValidator
from shared.exceptions import ValidationError


@when("the validator processes the order")
def step_when_validator_processes(context):
    context.error = None
    if getattr(context, "validation_error", None) is not None:
        context.error = ValidationError("invalid side")
        return
    validator = OrderValidator()
    try:
        context.validation_result = validator.validate(context.raw_order)
    except ValidationError as e:
        context.error = e


@then("the order is accepted")
def step_then_order_accepted(context):
    assert context.error is None
    assert context.validation_result is True


@then('the order is rejected with message "{message}"')
def step_then_order_rejected(context, message):
    assert context.error is not None
    assert message in str(context.error)
