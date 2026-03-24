# fix-protocol-simulator/tests/bdd/steps/trading_steps.py

from behave import given, when, then

from fix_simulator.exchange.order_book import OrderBook
from fix_simulator.exchange.matching_engine import MatchingEngine
from fix_simulator.exchange.order import Order


@given("the order book is empty")
def given_order_book_is_empty(context):
    context.book = OrderBook()
    context.engine = MatchingEngine(context.book)
    context.trade = None


@given("the following BUY orders are in the book")
def given_buy_orders_in_book(context):
    for row in context.table:
        context.engine.process_order(
            Order(row["order_id"], "BUY", float(row["price"]), int(row["quantity"]))
        )


@when("a BUY order is placed at price {price} for quantity {qty}")
def when_buy_order_placed(context, price, qty):
    context.engine.process_order(Order("B1", "BUY", float(price), int(qty)))


@when("a SELL order is placed at price {price} for quantity {qty}")
def when_sell_order_placed(context, price, qty):
    context.trade = context.engine.process_order(
        Order("S1", "SELL", float(price), int(qty))
    )


@then("a trade should be executed")
def then_trade_executed(context):
    assert context.trade is not None


@then("no trade should be executed")
def then_no_trade_executed(context):
    assert context.trade is None


@then("the trade price should be {price}")
def then_trade_price(context, price):
    assert context.trade["price"] == float(price)


@then("the trade quantity should be {qty}")
def then_trade_quantity(context, qty):
    assert context.trade["quantity"] == int(qty)


@then("the trade result should be {outcome}")
def then_trade_result(context, outcome):
    if outcome == "executed":
        assert context.trade is not None
    elif outcome == "no_trade":
        assert context.trade is None
