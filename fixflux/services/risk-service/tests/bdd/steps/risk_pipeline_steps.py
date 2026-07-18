from datetime import datetime, timezone
from unittest.mock import MagicMock

from behave import given, then, when

from risk_service.checker import RiskChecker
from risk_service.consumer import handle_order, handle_trade
from risk_service.position_store import PositionStore


def _default_checker(**overrides):
    params = dict(
        notional_limit=1_000_000.0,
        fat_finger_pct=10.0,
        gross_position_limit=100_000,
        net_position_limit=50_000,
        max_open_orders=100,
    )
    params.update(overrides)
    return RiskChecker(**params)


def _init_pipeline(context, **checker_overrides):
    context.store = PositionStore()
    context.last_prices = {}
    context.mock_producer = MagicMock()
    context.checker = _default_checker(**checker_overrides)


@given("the risk pipeline is running")
def step_given_pipeline(context):
    _init_pipeline(context)


@given("the risk pipeline is running with notional limit {limit:f}")
def step_given_pipeline_limited(context, limit):
    _init_pipeline(context, notional_limit=limit)


@given('an order for symbol "{symbol}" passes all risk checks')
def step_given_passing_order(context, symbol):
    context.order_dict = {
        "order_id": "ORD-001",
        "symbol": symbol,
        "side": "BUY",
        "price": 100.0,
        "quantity": 10,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_id": "CLIENT1",
    }


@given("an order with notional value above the limit")
def step_given_order_above_notional(context):
    context.order_dict = {
        "order_id": "ORD-001",
        "symbol": "AAPL",
        "side": "BUY",
        "price": 999_999.0,
        "quantity": 999,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_id": "CLIENT1",
    }


@given('a trade for symbol "{symbol}" at price {price:f}')
def step_given_trade(context, symbol, price):
    context.trade_dict = {
        "trade_id": "TRD-001",
        "symbol": symbol,
        "buy_order_id": "ORD-BUY",
        "sell_order_id": "ORD-SELL",
        "price": price,
        "quantity": 100,
    }


@when("the pipeline processes the order")
def step_when_pipeline_processes_order(context):
    handle_order(
        context.order_dict,
        context.checker,
        context.store,
        context.last_prices,
        context.mock_producer,
    )


@when("the pipeline processes the trade")
def step_when_pipeline_processes_trade(context):
    handle_trade(context.trade_dict, context.store, context.last_prices)


@then("the approved topic receives {count:d} message")
@then("the approved topic receives {count:d} messages")
def step_then_approved_count(context, count):
    assert (
        context.mock_producer.approve.call_count == count
    ), f"Expected {count} approve calls, got {context.mock_producer.approve.call_count}"


@then("the rejected topic receives {count:d} message")
@then("the rejected topic receives {count:d} messages")
def step_then_rejected_count(context, count):
    assert (
        context.mock_producer.reject.call_count == count
    ), f"Expected {count} reject calls, got {context.mock_producer.reject.call_count}"


@then('the last price for "{symbol}" is {price:f}')
def step_then_last_price(context, symbol, price):
    actual = context.last_prices.get(symbol)
    assert actual == price, f"Expected last price {price} for {symbol}, got {actual}"
