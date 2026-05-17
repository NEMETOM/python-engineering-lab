from behave import given, then, use_step_matcher, when
from matching_engine.models import Order
from matching_engine.order_book import OrderBook

# Use regex matching so numeric patterns don't swallow "absent" steps.
use_step_matcher("re")


# ── Givens ───────────────────────────────────────────────────────────────────


@given("an empty order book")
def given_empty_order_book(context):
    context.book = OrderBook()


# ── Whens ────────────────────────────────────────────────────────────────────


@when(
    r'I add a (?P<side>BUY|SELL) order "(?P<order_id>[^"]+)" at price (?P<price>[\d.]+) for quantity (?P<quantity>\d+)'
)
def when_add_order_to_book(context, side, order_id, price, quantity):
    context.book.add_order(Order(order_id, side, float(price), int(quantity)))


# ── Thens ────────────────────────────────────────────────────────────────────


@then(r"the best (?P<side>bid|ask) price is (?P<price>[\d.]+)")
def then_best_price(context, side, price):
    if side == "bid":
        assert context.book.best_bid() is not None
        assert context.book.best_bid().price == float(price)
    else:
        assert context.book.best_ask() is not None
        assert context.book.best_ask().price == float(price)


@then(r"the best (?P<side>bid|ask) price is absent")
def then_best_price_is_absent(context, side):
    if side == "bid":
        assert context.book.best_bid() is None
    else:
        assert context.book.best_ask() is None
