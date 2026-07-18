from datetime import datetime, timezone

from behave import given, then, when

from risk_service.checker import RiskChecker
from risk_service.models import ValidatedOrder
from risk_service.position_store import PositionStore


def _make_checker_with_store(context, **kwargs):
    defaults = dict(
        notional_limit=1_000_000.0,
        fat_finger_pct=10.0,
        gross_position_limit=100_000,
        net_position_limit=100_000,
        max_open_orders=100,
    )
    defaults.update(kwargs)
    context.checker = RiskChecker(**defaults)
    context.store = PositionStore()


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


@given("a risk checker with gross position limit {limit:d}")
def step_given_gross_limit(context, limit):
    _make_checker_with_store(
        context, gross_position_limit=limit, net_position_limit=limit
    )


@given("a risk checker with max open orders {max:d}")
def step_given_max_open_orders(context, max):
    _make_checker_with_store(context, max_open_orders=max)


@given('a flat position for client "{client_id}" symbol "{symbol}"')
def step_given_flat_position(context, client_id, symbol):
    pass  # PositionStore starts flat by default


@given(
    'a position order for "{client_id}" symbol "{symbol}" side "{side}" quantity {qty:d}'
)
def step_given_position_order(context, client_id, symbol, side, qty):
    context.order = _make_order(
        client_id=client_id, symbol=symbol, side=side, quantity=qty
    )


@given('client "{client_id}" has {count:d} open orders')
def step_given_open_orders(context, client_id, count):
    for i in range(count):
        context.store.record_open_order(f"ORD-{i}", client_id, "AAPL", "BUY", 100)


@given('a new order from client "{client_id}"')
def step_given_new_order(context, client_id):
    context.order = _make_order(client_id=client_id)


@when("the position check runs")
def step_when_position_check(context):
    context.decision = context.checker.check_position(context.order, context.store)


@when("the open order count check runs")
def step_when_open_order_check(context):
    context.decision = context.checker.check_open_orders(context.order, context.store)


@when("{count:d} open orders are filled by trades")
@when("{count:d} open order is filled by a trade")
def step_when_fill_orders(context, count):
    for i in range(count):
        context.store.fill_order(f"ORD-{i}")


@then('client "{client_id}" can place a new order: {can_place}')
def step_then_can_place(context, client_id, can_place):
    order = _make_order(client_id=client_id)
    decision = context.checker.check_open_orders(order, context.store)
    expected = can_place.lower() == "true"
    assert decision.approved == expected, (
        f"Expected can_place={expected}, got approved={decision.approved}: {decision.reason}"
    )
