from behave import given, then, use_step_matcher, when

from market_data_service.market_cache import MarketCache
from market_data_service.publisher import MarketPublisher

# Use regex matching so numeric patterns don't swallow "absent" steps.
use_step_matcher("re")


# ── Givens ───────────────────────────────────────────────────────────────────


@given("a fresh market cache")
def a_fresh_market_cache(context):
    context.cache = MarketCache()


# ── Whens ────────────────────────────────────────────────────────────────────


@when(r"trade price (?P<price>[\d.]+) is received")
def receive_trade(context, price):
    context.cache.update_trade({"price": float(price)})


@when(r"order book update with bid (?P<bid>[\d.]+) and ask (?P<ask>[\d.]+) is received")
def receive_order_book(context, bid, ask):
    context.cache.update_order_book({"best_bid": float(bid), "best_ask": float(ask)})


@when("the publisher publishes")
def publisher_publishes(context):
    publisher = MarketPublisher(context.cache)
    publisher.publish()
    context.published_snapshot = context.cache.snapshot()


# ── Thens ────────────────────────────────────────────────────────────────────


@then(r"last trade price is (?P<price>[\d.]+)")
def check_last_trade_price(context, price):
    assert context.cache.snapshot()["last_trade_price"] == float(price)


@then("last trade price is absent")
def check_last_trade_price_absent(context):
    assert context.cache.snapshot()["last_trade_price"] is None


@then(r"best bid is (?P<bid>[\d.]+)")
def check_best_bid(context, bid):
    assert context.cache.snapshot()["best_bid"] == float(bid)


@then("best bid is absent")
def check_best_bid_absent(context):
    assert context.cache.snapshot()["best_bid"] is None


@then(r"best ask is (?P<ask>[\d.]+)")
def check_best_ask(context, ask):
    assert context.cache.snapshot()["best_ask"] == float(ask)


@then("best ask is absent")
def check_best_ask_absent(context):
    assert context.cache.snapshot()["best_ask"] is None


@then(r"mid price is (?P<mid>[\d.]+)")
def check_mid_price(context, mid):
    assert context.cache.snapshot()["mid_price"] == float(mid)


@then("mid price is absent")
def check_mid_price_absent(context):
    assert context.cache.snapshot()["mid_price"] is None


@then(r"the published snapshot contains last trade price (?P<price>[\d.]+)")
def check_published_last_trade(context, price):
    assert context.published_snapshot["last_trade_price"] == float(price)


@then(r"the published snapshot contains best bid (?P<bid>[\d.]+)")
def check_published_best_bid(context, bid):
    assert context.published_snapshot["best_bid"] == float(bid)


@then(r"the published snapshot contains best ask (?P<ask>[\d.]+)")
def check_published_best_ask(context, ask):
    assert context.published_snapshot["best_ask"] == float(ask)
