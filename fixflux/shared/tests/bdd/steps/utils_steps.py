from datetime import datetime, timezone

from behave import given, then, when
from shared.utils.time import to_iso, utc_now


@when("utc_now is called")
def step_when_utc_now(context):
    context.result = utc_now()


@then("the result is a datetime instance")
def step_then_is_datetime(context):
    assert isinstance(context.result, datetime)


@then("the result is timezone-aware")
def step_then_is_timezone_aware(context):
    assert context.result.tzinfo is not None


@then("the result timezone is UTC")
def step_then_is_utc(context):
    assert context.result.tzinfo == timezone.utc


@given('the UTC datetime "{input}"')
def step_given_utc_datetime(context, input):
    context.dt = datetime.fromisoformat(input)


@when("to_iso is called with that datetime")
def step_when_to_iso(context):
    context.iso_result = to_iso(context.dt)


@then('the ISO result is "{expected}"')
def step_then_iso_result(context, expected):
    assert context.iso_result == expected


@then("parsing the ISO result yields the original datetime")
def step_then_iso_parseable(context):
    assert datetime.fromisoformat(context.iso_result) == context.dt
