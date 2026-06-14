from behave import given, then, when

from compliance_service.rules.surveillance.rapid_fire import RapidFireRule
from compliance_service.rules.surveillance.repeated_orders import RepeatedOrdersRule
from compliance_service.rules.surveillance.wash_trading import WashTradingRule


@given("a wash trading rule with a {window:d}-second window")
def step_wash_rule(context, window):
    context.rule = WashTradingRule({"enabled": True, "window_seconds": window})


@when('client "{client}" submits a "{side1}" then a "{side2}" order for "{symbol}"')
def step_wash_submit(context, client, side1, side2, symbol):
    context.rule.check({"client_id": client, "symbol": symbol, "side": side1})
    context.violation = context.rule.check(
        {"client_id": client, "symbol": symbol, "side": side2}
    )


@then('the wash trading alert is "{outcome}"')
def step_wash_outcome(context, outcome):
    if outcome == "triggered":
        assert context.violation is not None, "Expected wash trading alert but got None"
        assert context.violation.severity.value == "CRITICAL"
    else:
        assert (
            context.violation is None
        ), f"Expected no alert but got: {context.violation}"


@given("a rapid fire rule allowing {limit:d} orders per 60 seconds")
def step_rapid_rule(context, limit):
    context.rule = RapidFireRule(
        {"enabled": True, "max_orders": limit, "window_seconds": 60}
    )


@when('client "CLIENT1" submits {count:d} orders within the window')
def step_rapid_submit(context, count):
    event = {"client_id": "CLIENT1", "symbol": "EURUSD"}
    context.violation = None
    for _ in range(count):
        result = context.rule.check(event)
        if result:
            context.violation = result


@then('the rapid fire alert is "{outcome}"')
def step_rapid_outcome(context, outcome):
    if outcome == "triggered":
        assert context.violation is not None, "Expected rapid fire alert but got None"
    else:
        assert (
            context.violation is None
        ), f"Expected no alert but got: {context.violation}"


@given("a repeated orders rule with threshold {threshold:d}")
def step_repeated_rule(context, threshold):
    context.rule = RepeatedOrdersRule(
        {"enabled": True, "repeat_threshold": threshold, "window_seconds": 300}
    )


@when('client "CLIENT1" submits the same order {count:d} times')
def step_repeated_submit(context, count):
    event = {
        "client_id": "CLIENT1",
        "symbol": "EURUSD",
        "side": "BUY",
        "price": 1.09,
        "quantity": 100,
    }
    context.violation = None
    for _ in range(count):
        result = context.rule.check(event)
        if result:
            context.violation = result


@then('the repeated orders alert is "{outcome}"')
def step_repeated_outcome(context, outcome):
    if outcome == "triggered":
        assert (
            context.violation is not None
        ), "Expected repeated orders alert but got None"
    else:
        assert (
            context.violation is None
        ), f"Expected no alert but got: {context.violation}"
