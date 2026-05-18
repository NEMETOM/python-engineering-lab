from behave import given, then, use_step_matcher, when
from matching_engine.engine import MatchingEngine
from matching_engine.models import Order
from matching_engine.order_book import OrderBook

# Use regex matching so numeric patterns don't swallow literal-text steps.
use_step_matcher("re")


# ── Givens ───────────────────────────────────────────────────────────────────


@given("an empty order book and matching engine")
def given_empty_engine(context):
    context.book = OrderBook()
    context.engine = MatchingEngine(context.book)
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
