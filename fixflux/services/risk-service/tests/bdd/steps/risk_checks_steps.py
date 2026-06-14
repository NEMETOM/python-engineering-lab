from datetime import datetime, timezone

from behave import given, when

from risk_service.checker import RiskChecker
from risk_service.models import ValidatedOrder


def _make_checker(**kwargs):
    defaults = dict(
        notional_limit=1_000_000.0,
        fat_finger_pct=10.0,
        gross_position_limit=100_000,
        net_position_limit=50_000,
        max_open_orders=100,
    )
    defaults.update(kwargs)
    return RiskChecker(**defaults)


def _make_order(**kwargs):
    defaults = dict(
        order_id="test-order",
        symbol="AAPL",
        side="BUY",
        price=100.0,
        quantity=10,
        timestamp=datetime.now(timezone.utc),
        client_id="CLIENT1",
    )
    defaults.update(kwargs)
    return ValidatedOrder(**defaults)


@given("a risk checker with notional limit {limit:f}")
def step_given_notional_limit(context, limit):
    context.checker = _make_checker(notional_limit=limit)


@given("a risk checker with fat-finger threshold {pct:f}%")
def step_given_fat_finger_pct(context, pct):
    context.checker = _make_checker(fat_finger_pct=pct)


@given('an order for symbol "{symbol}" side "{side}" price {price:f} quantity {qty:d}')
def step_given_order_full(context, symbol, side, price, qty):
    context.order = _make_order(symbol=symbol, side=side, price=price, quantity=qty)


@given('an order for symbol "{symbol}" price {price:f}')
def step_given_order_price(context, symbol, price):
    context.order = _make_order(symbol=symbol, price=price)


@given('the last trade price for "{symbol}" is {price:f}')
def step_given_last_price(context, symbol, price):
    if not hasattr(context, "last_prices"):
        context.last_prices = {}
    context.last_prices[symbol] = price


@given('no last trade price exists for "{symbol}"')
def step_given_no_last_price(context, symbol):
    context.last_prices = {}


@when("the notional check runs")
def step_when_notional_check(context):
    context.decision = context.checker.check_notional(context.order)


@when("the fat-finger check runs")
def step_when_fat_finger_check(context):
    last_prices = getattr(context, "last_prices", {})
    last_price = last_prices.get(context.order.symbol, 0.0)
    context.decision = context.checker.check_fat_finger(context.order, last_price)
