from datetime import datetime

from behave import given
from order_service.schemas import RawOrderEvent
from pydantic import ValidationError


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
            timestamp=datetime.utcnow(),
        )
    except ValidationError as exc:
        context.raw_order = None
        context.validation_error = exc
    context.msg_value = dict(
        symbol=symbol,
        side=side,
        price=price,
        quantity=quantity,
        timestamp=datetime.utcnow().isoformat(),
    )
