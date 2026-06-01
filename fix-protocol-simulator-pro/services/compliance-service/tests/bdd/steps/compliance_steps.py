from behave import given, then, when

from compliance_service.config import load_policies
from compliance_service.engine.rules_engine import RulesEngine
from compliance_service.rules.compliance.duplicate_order import DuplicateOrderRule
from compliance_service.rules.compliance.invalid_symbol import InvalidSymbolRule
from compliance_service.rules.compliance.trade_size import TradeSizeRule
from compliance_service.rules.loader import build_compliance_rules


@given("a compliance rules engine with default policies")
def step_default_engine(context):
    policies = load_policies()
    context.engine = RulesEngine(build_compliance_rules(policies))


@when(
    'an order arrives with client_id "{client_id}", symbol "{symbol}", '
    "quantity {qty:d}, price {price:f}"
)
def step_order_arrives(context, client_id, symbol, qty, price):
    context.event = {
        "client_id": client_id,
        "symbol": symbol,
        "quantity": qty,
        "price": price,
    }
    context.violations = context.engine.evaluate(context.event)


@then('the rule "{rule}" is "{outcome}" with severity "{severity}"')
def step_rule_outcome(context, rule, outcome, severity):
    matched = [v for v in context.violations if v.rule_name == rule]
    if outcome == "triggered":
        assert matched, f"Expected {rule} to trigger but it did not"
        assert (
            matched[0].severity.value == severity
        ), f"Expected severity {severity}, got {matched[0].severity.value}"
    else:
        assert not matched, f"Expected {rule} NOT to trigger but it did: {matched}"


@given("a trade size rule with default limit {limit:d}")
def step_trade_size_rule(context, limit):
    context.rule = TradeSizeRule({"enabled": True, "max_quantity": {"default": limit}})


@when('an order for symbol "{symbol}" with quantity {qty:d} is evaluated')
def step_evaluate_trade_size(context, symbol, qty):
    context.violation = context.rule.check(
        {"client_id": "C1", "symbol": symbol, "quantity": qty}
    )


@then('the trade size violation is "{outcome}"')
def step_trade_size_outcome(context, outcome):
    if outcome == "triggered":
        assert context.violation is not None, "Expected violation but got None"
    else:
        assert (
            context.violation is None
        ), f"Expected no violation but got: {context.violation}"


@given('a symbol rule allowing only "{symbols}"')
def step_symbol_rule(context, symbols):
    symbol_list = [s.strip() for s in symbols.split(",")]
    context.rule = InvalidSymbolRule({"enabled": True, "symbols": symbol_list})


@when('an order for symbol "{symbol}" is evaluated')
def step_evaluate_symbol(context, symbol):
    context.violation = context.rule.check({"client_id": "C1", "symbol": symbol})


@then('the invalid symbol violation is "{outcome}"')
def step_symbol_outcome(context, outcome):
    if outcome == "triggered":
        assert context.violation is not None
        assert context.violation.severity.value == "CRITICAL"
    else:
        assert context.violation is None


@given("a duplicate order rule with a {window:d}-second window")
def step_dup_rule(context, window):
    context.rule = DuplicateOrderRule({"enabled": True, "window_seconds": window})


@when("the same order is submitted {times:d} times")
def step_submit_same_order(context, times):
    event = {
        "client_id": "C1",
        "symbol": "EURUSD",
        "side": "BUY",
        "price": "1.09",
        "quantity": "100",
    }
    context.violations = []
    for _ in range(times):
        result = context.rule.check(event)
        context.violations.append(result)


@then('the duplicate violation fires on the "{fire_on}" submission')
def step_dup_fires_on(context, fire_on):
    ordinal_map = {"first": 0, "second": 1, "third": 2}
    idx = ordinal_map[fire_on]
    for i, v in enumerate(context.violations):
        if i == idx:
            assert v is not None, f"Expected violation at index {idx} but got None"
        else:
            assert v is None, f"Expected no violation at index {i} but got {v}"
