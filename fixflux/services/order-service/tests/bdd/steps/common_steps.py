from datetime import UTC, datetime

from behave import given
from pydantic import ValidationError

from order_service.schemas import RawOrderEvent


@given(
    'a raw order with symbol "{symbol}", side "{side}", price {price:f}, quantity {quantity:d}'
)
def step_given_raw_order(context, symbol, side, price, quantity):
    context.validation_error = None
    try:
        context.raw_order = RawOrderEvent(
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            timestamp=datetime.now(tz=UTC),
        )
    except ValidationError as exc:
        context.raw_order = None
        context.validation_error = exc
    context.msg_value = {
        "symbol": symbol,
        "side": side,
        "price": price,
        "quantity": quantity,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
