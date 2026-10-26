from behave import given, then, use_step_matcher, when

from matching_engine.engine import MatchingEngine
from matching_engine.models import Order

# Use regex matching so numeric patterns don't swallow literal-text steps.
use_step_matcher("re")


# ── Givens ───────────────────────────────────────────────────────────────────


@given("an empty order book and matching engine")
def given_empty_engine(context):
    # The engine owns one book per symbol; these steps use Order's default
    # symbol "", so they work on that book directly.
    context.engine = MatchingEngine()
    context.book = context.engine.books[""]
    context.trades = []
    context.last_order = None


@given(
    r'a resting (?P<side>BUY|SELL) order "(?P<order_id>[^"]+)" at price (?P<price>[\d.]+) for quantity (?P<quantity>\d+)'
)
def given_resting_order(context, side, order_id, price, quantity):
    context.book.add_order(Order(order_id, side, float(price), int(quantity)))


# ── Whens ────────────────────────────────────────────────────────────────────


@when(
    r'I submit a (?P<side>BUY|SELL) order "(?P<order_id>[^"]+)" at price (?P<price>[\d.]+) for quantity (?P<quantity>\d+)'
)
def when_submit_order(context, side, order_id, price, quantity):
    order = Order(order_id, side, float(price), int(quantity))
    context.last_order = order
    context.trades = context.engine.process(order)


# ── Thens ────────────────────────────────────────────────────────────────────


@then(r"(?P<count>\d+) trade\(s\) are produced")
def then_trade_count(context, count):
    assert len(context.trades) == int(count)


@then(r"the executed trade quantity is (?P<quantity>\d+)")
def then_executed_trade_quantity(context, quantity):
    assert context.trades[0].quantity == int(quantity)


@then(r"the executed trade price is (?P<price>[\d.]+)")
def then_executed_trade_price(context, price):
    assert context.trades[0].price == float(price)


@then("the incoming order rests in the book")
def then_incoming_order_in_book(context):
    order = context.last_order
    side_list = context.book.buys if order.side == "BUY" else context.book.sells
    assert order in side_list


@then(r"the incoming order rests in the book with quantity (?P<quantity>\d+)")
def then_incoming_order_in_book_with_quantity(context, quantity):
    order = context.last_order
    side_list = context.book.buys if order.side == "BUY" else context.book.sells
    assert order in side_list
    assert order.quantity == int(quantity)


@then(
    r'resting order "(?P<order_id>[^"]+)" is first in the book with quantity (?P<quantity>\d+)'
)
def then_resting_order_first_with_quantity(context, order_id, quantity):
    resting_side = "SELL" if context.last_order.side == "BUY" else "BUY"
    side_list = context.book.sells if resting_side == "SELL" else context.book.buys
    assert side_list, "resting side is empty - the remainder was lost"
    assert side_list[0].order_id == order_id, [o.order_id for o in side_list]
    assert side_list[0].quantity == int(quantity)


@then(
    r"the trade reports (?P<resting>\d+) left open on the resting side and "
    r"(?P<incoming>\d+) on the incoming side"
)
def then_trade_leaves(context, resting, incoming):
    trade = context.trades[0]
    if context.last_order.side == "BUY":
        incoming_leaves, resting_leaves = trade.buy_leaves_qty, trade.sell_leaves_qty
    else:
        incoming_leaves, resting_leaves = trade.sell_leaves_qty, trade.buy_leaves_qty
    assert (resting_leaves, incoming_leaves) == (int(resting), int(incoming))
