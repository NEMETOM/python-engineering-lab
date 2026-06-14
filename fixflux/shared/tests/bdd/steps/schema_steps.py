from behave import given, then
from pydantic import ValidationError as PydanticValidationError
from shared.schemas.book_event import BookEvent
from shared.schemas.order_event import OrderEvent
from shared.schemas.trade_event import TradeEvent


def _default_order(**overrides):
    base = dict(order_id="O1", symbol="AAPL", side="BUY", price=100.0, quantity=10)
    return {**base, **overrides}


def _default_trade(**overrides):
    base = dict(
        trade_id="T001",
        symbol="AAPL",
        buy_order_id="B001",
        sell_order_id="S001",
        price=150.0,
        quantity=10,
    )
    return {**base, **overrides}


# --- OrderEvent steps ---


@given('an order event with side "{side}", price {price:f}, quantity {quantity:d}')
def step_given_order_event(context, side, price, quantity):
    context.event = None
    context.error = None
    try:
        context.event = OrderEvent(
            **_default_order(side=side, price=price, quantity=quantity)
        )
    except PydanticValidationError as e:
        context.error = e


@given(
    'an order event with side "{side}", price {price:f}, quantity {quantity:d} -- invalid'
)
def step_given_invalid_order_event(context, side, price, quantity):
    step_given_order_event(context, side, price, quantity)


@given('an order event with side "BUY", price {price:f}, quantity 10')
def step_given_order_with_price(context, price):
    step_given_order_event(context, "BUY", price, 10)


@given('an order event with side "BUY", price 100.0, quantity {quantity:d}')
def step_given_order_with_quantity(context, quantity):
    step_given_order_event(context, "BUY", 100.0, quantity)


@given('an order event is missing the "{field}" field')
def step_given_order_missing_field(context, field):
    data = _default_order()
    del data[field]
    context.event = None
    context.error = None
    try:
        context.event = OrderEvent(**data)
    except PydanticValidationError as e:
        context.error = e


@then("the order event is valid")
def step_then_order_valid(context):
    assert context.error is None
    assert context.event is not None


@then("the order event is invalid")
def step_then_order_invalid(context):
    assert context.error is not None


@then('the order event side is "{side}"')
def step_then_order_side(context, side):
    assert context.event.side == side


# --- TradeEvent steps ---


@given('a trade event with trade_id "{trade_id}", symbol "{symbol}", price {price:f}')
def step_given_trade_event(context, trade_id, symbol, price):
    context.event = None
    context.error = None
    try:
        context.event = TradeEvent(
            **_default_trade(trade_id=trade_id, symbol=symbol, price=price)
        )
    except PydanticValidationError as e:
        context.error = e


@given('a trade event is missing the "{field}" field')
def step_given_trade_missing_field(context, field):
    data = _default_trade()
    del data[field]
    context.event = None
    context.error = None
    try:
        context.event = TradeEvent(**data)
    except PydanticValidationError as e:
        context.error = e


@given('a trade event with an invalid "{field}" value "{value}"')
def step_given_trade_invalid_field(context, field, value):
    data = _default_trade(**{field: value})
    context.event = None
    context.error = None
    try:
        context.event = TradeEvent(**data)
    except PydanticValidationError as e:
        context.error = e


@then("the trade event is valid")
def step_then_trade_valid(context):
    assert context.error is None
    assert context.event is not None


@then("the trade event is invalid")
def step_then_trade_invalid(context):
    assert context.error is not None


@then('the trade event trade_id is "{trade_id}"')
def step_then_trade_id(context, trade_id):
    assert context.event.trade_id == trade_id


# --- BookEvent steps ---


@given('a book event with symbol "{symbol}"')
def step_given_book_event_symbol_only(context, symbol):
    context.event = None
    context.error = None
    try:
        context.event = BookEvent(symbol=symbol)
    except PydanticValidationError as e:
        context.error = e


@given('a book event with symbol "{symbol}", best_bid {bid:f} and best_ask {ask:f}')
def step_given_book_event_bid_ask(context, symbol, bid, ask):
    context.event = None
    context.error = None
    try:
        context.event = BookEvent(symbol=symbol, best_bid=bid, best_ask=ask)
    except PydanticValidationError as e:
        context.error = e


@given(
    'a book event with symbol "{symbol}", mid_price {mid:f} and last_trade_price {last:f}'
)
def step_given_book_event_mid_last(context, symbol, mid, last):
    context.event = None
    context.error = None
    try:
        context.event = BookEvent(symbol=symbol, mid_price=mid, last_trade_price=last)
    except PydanticValidationError as e:
        context.error = e


@given("a book event with no symbol")
def step_given_book_event_no_symbol(context):
    context.event = None
    context.error = None
    try:
        context.event = BookEvent()
    except PydanticValidationError as e:
        context.error = e


@then("the book event is valid")
def step_then_book_valid(context):
    assert context.error is None
    assert context.event is not None


@then("the book event is invalid")
def step_then_book_invalid(context):
    assert context.error is not None


@then("best_bid is absent")
def step_then_best_bid_absent(context):
    assert context.event.best_bid is None


@then("best_ask is absent")
def step_then_best_ask_absent(context):
    assert context.event.best_ask is None


@then("best_bid is {bid:f}")
def step_then_best_bid(context, bid):
    assert context.event.best_bid == bid


@then("best_ask is {ask:f}")
def step_then_best_ask(context, ask):
    assert context.event.best_ask == ask


@then("mid_price is {mid:f}")
def step_then_mid_price(context, mid):
    assert context.event.mid_price == mid


@then("last_trade_price is {last:f}")
def step_then_last_trade_price(context, last):
    assert context.event.last_trade_price == last
