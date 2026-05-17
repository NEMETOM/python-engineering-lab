from datetime import datetime
from unittest.mock import MagicMock

from behave import given
from trade_store.schemas.trade_event import TradeEvent


@given(
    'a trade event with trade_id "{trade_id}", symbol "{symbol}", buy_order_id "{buy}", sell_order_id "{sell}", price {price:f}, quantity {quantity:d}'
)
def step_given_trade_event(context, trade_id, symbol, buy, sell, price, quantity):
    context.trade_event = TradeEvent(
        trade_id=trade_id,
        symbol=symbol,
        buy_order_id=buy,
        sell_order_id=sell,
        price=price,
        quantity=quantity,
        timestamp=datetime.utcnow(),
    )
    context.msg_value = dict(
        trade_id=trade_id,
        symbol=symbol,
        buy_order_id=buy,
        sell_order_id=sell,
        price=price,
        quantity=quantity,
        timestamp=datetime.utcnow().isoformat(),
    )
    msg = MagicMock()
    msg.value = context.msg_value
    context.messages = [msg]
    context.error = None
    context.repo_side_effect = None
