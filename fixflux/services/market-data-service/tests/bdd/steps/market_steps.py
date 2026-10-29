from unittest.mock import patch

from behave import given, then, use_step_matcher, when

from market_data_service.market_cache import MarketCache
from market_data_service.publisher import MarketPublisher

# Regex matching so numeric patterns don't swallow "absent"/"none" steps.
use_step_matcher("re")

_PRICE = r"[\d.]+|none"


def _price(text: str) -> float | None:
    return None if text == "none" else float(text)


def _snapshot(context, symbol: str) -> dict:
    snapshots = context.cache.snapshot()
    assert symbol in snapshots, f"no snapshot for {symbol}: {list(snapshots)}"
    return snapshots[symbol]


def _sent_snapshots(context) -> list[tuple[str, dict]]:
    return [c.args for c in context.producer.send.call_args_list]


# ── Givens ───────────────────────────────────────────────────────────────────


@given("a fresh market cache")
def a_fresh_market_cache(context):
    context.cache = MarketCache()


@given("a market data publisher")
def a_market_data_publisher(context):
    # The repo's single Kafka patch target: the shared factory's KafkaProducer.
    # The publisher keeps the mocked producer after the patch exits.
    with patch("shared.infrastructure.kafka_client.KafkaProducer") as producer_cls:
        context.publisher = MarketPublisher(context.cache)
    context.producer = producer_cls.return_value


# ── Whens ────────────────────────────────────────────────────────────────────


@when(rf'a trade for "(?P<symbol>[A-Z]+)" at (?P<price>{_PRICE}) is received')
def receive_trade(context, symbol, price):
    context.cache.update_trade({"symbol": symbol, "price": float(price)})


@when(
    rf'an order book update for "(?P<symbol>[A-Z]+)" with bid (?P<bid>{_PRICE}) '
    rf"and ask (?P<ask>{_PRICE}) is received"
)
def receive_order_book(context, symbol, bid, ask):
    context.cache.update_order_book(
        {"symbol": symbol, "best_bid": _price(bid), "best_ask": _price(ask)}
    )


@when("the publisher publishes")
def publisher_publishes(context):
    context.publisher.publish()


# ── Thens ────────────────────────────────────────────────────────────────────


@then(r'there is no snapshot for "(?P<symbol>[A-Z]+)"')
def check_no_snapshot(context, symbol):
    assert symbol not in context.cache.snapshot()


@then(rf'the last trade price for "(?P<symbol>[A-Z]+)" is (?P<price>{_PRICE})')
def check_last_trade_price(context, symbol, price):
    assert _snapshot(context, symbol)["last_trade_price"] == _price(price)


@then(rf'the best bid for "(?P<symbol>[A-Z]+)" is (?P<bid>{_PRICE})')
def check_best_bid(context, symbol, bid):
    assert _snapshot(context, symbol)["best_bid"] == _price(bid)


@then(rf'the best ask for "(?P<symbol>[A-Z]+)" is (?P<ask>{_PRICE})')
def check_best_ask(context, symbol, ask):
    assert _snapshot(context, symbol)["best_ask"] == _price(ask)


@then(r'the mid price for "(?P<symbol>[A-Z]+)" is (?P<mid>[\d.]+)')
def check_mid_price(context, symbol, mid):
    actual = _snapshot(context, symbol)["mid_price"]
    assert actual is not None and abs(actual - float(mid)) < 1e-9, actual


@then(r'the mid price for "(?P<symbol>[A-Z]+)" is absent')
def check_mid_price_absent(context, symbol):
    assert _snapshot(context, symbol)["mid_price"] is None


@then(
    r'(?P<count>\d+) snapshot(?:\(s\) are|s are| is) sent to the "(?P<topic>[a-z_]+)" topic'
)
def check_sent_count(context, count, topic):
    sent = _sent_snapshots(context)
    assert len(sent) == int(count), sent
    assert all(t == topic for t, _ in sent), sent


@then(
    rf'the sent snapshot for "(?P<symbol>[A-Z]+)" has bid (?P<bid>{_PRICE}), '
    rf"ask (?P<ask>{_PRICE}) and last trade price (?P<price>{_PRICE})"
)
def check_sent_snapshot(context, symbol, bid, ask, price):
    payloads = [p for _, p in _sent_snapshots(context) if p["symbol"] == symbol]
    assert payloads, f"nothing sent for {symbol}"
    sent = payloads[-1]
    assert sent["best_bid"] == _price(bid), sent
    assert sent["best_ask"] == _price(ask), sent
    assert sent["last_trade_price"] == _price(price), sent
