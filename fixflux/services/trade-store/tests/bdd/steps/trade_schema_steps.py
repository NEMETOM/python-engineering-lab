from datetime import datetime

from behave import given, then
from pydantic import ValidationError

from trade_store.schemas.trade_event import TradeEvent


def _valid_fields(**overrides):
    base = dict(
        trade_id="T001",
        symbol="AAPL",
        buy_order_id="B001",
        sell_order_id="S001",
        price=150.0,
        quantity=10,
        timestamp=datetime.utcnow(),
    )
    return {**base, **overrides}


@given('a trade event is missing the "{field}" field')
def step_given_missing_field(context, field):
    data = _valid_fields()
    del data[field]
    context.error = None
    try:
        context.trade_event = TradeEvent(**data)
    except (ValidationError, Exception) as e:
        context.error = e


@given('a trade event has an invalid "{field}" value of "{value}"')
def step_given_invalid_field(context, field, value):
    data = _valid_fields(**{field: value})
    context.error = None
    try:
        context.trade_event = TradeEvent(**data)
    except (ValidationError, Exception) as e:
        context.error = e


@then("the trade event is valid")
def step_then_trade_event_valid(context):
    assert context.error is None
    assert context.trade_event is not None


@then("the trade event is invalid")
def step_then_trade_event_invalid(context):
    assert context.error is not None


@then('the trade event has symbol "{symbol}"')
def step_then_trade_event_symbol(context, symbol):
    assert context.trade_event.symbol == symbol


@then("the trade event has price {price:f}")
def step_then_trade_event_price(context, price):
    assert context.trade_event.price == price
