import uuid
from datetime import datetime, timezone

from behave import given, then, when


def _build_trade_payload(symbol, price, quantity):
    trade_id = f"KIT-{uuid.uuid4().hex[:12]}"
    return trade_id, {
        "trade_id": trade_id,
        "symbol": symbol,
        "buy_order_id": f"B-{trade_id}",
        "sell_order_id": f"S-{trade_id}",
        "price": float(price),
        "quantity": int(quantity),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Givens ────────────────────────────────────────────────────────────────────


@given(
    'a valid trade message for symbol "{symbol}" at price {price:f} '
    "and quantity {quantity:d} is published to the trades topic"
)
def step_publish_valid_trade(context, symbol, price, quantity):
    from shared.infrastructure.kafka_client import create_producer

    trade_id, payload = _build_trade_payload(symbol, price, quantity)
    context.expected_trade_id = trade_id
    context.expected_symbol = symbol
    context.expected_price = price

    producer = create_producer()
    producer.send("trades", payload)
    producer.flush()


@given("a malformed message is published to the trades topic")
def step_publish_malformed(context):
    from shared.infrastructure.kafka_client import create_producer

    producer = create_producer()
    producer.send("trades", {"garbage": True, "not_a_trade": "at_all"})
    producer.flush()


# ── Whens ─────────────────────────────────────────────────────────────────────


@when("the consumer pipeline processes available messages")
def step_run_consumer(context):
    from trade_store.repository import TradeRepository
    from trade_store.schemas import TradeEvent

    repo = TradeRepository()
    context.consumer_errors = []

    # context.kafka_consumer was created in before_scenario with auto_offset_reset=latest
    # and an initial poll() to position at the end of the topic BEFORE the Given step
    # published. It will drain all messages added since that point, then time out.
    for msg in context.kafka_consumer:
        try:
            event = TradeEvent(**msg.value)
            repo.save(event)
        except Exception as exc:
            context.consumer_errors.append(str(exc))


# ── Thens ─────────────────────────────────────────────────────────────────────


@then(
    'the expected trade for symbol "{symbol}" at price {price:f} is in the database'
)
def step_then_trade_with_price(context, symbol, price):
    from trade_store.repository import TradeRepository

    trade = TradeRepository().get_by_id(context.expected_trade_id)
    assert trade is not None, (
        f"Trade {context.expected_trade_id} not found in the database"
    )
    assert trade["symbol"] == symbol, (
        f"symbol: expected {symbol!r}, got {trade['symbol']!r}"
    )
    assert abs(trade["price"] - price) < 0.001, (
        f"price: expected {price}, got {trade['price']}"
    )


@then('the expected trade for symbol "{symbol}" is in the database')
def step_then_trade_by_symbol(context, symbol):
    from trade_store.repository import TradeRepository

    trade = TradeRepository().get_by_id(context.expected_trade_id)
    assert trade is not None, (
        f"Trade {context.expected_trade_id} not found in the database"
    )
    assert trade["symbol"] == symbol, (
        f"symbol: expected {symbol!r}, got {trade['symbol']!r}"
    )


@then("the malformed message was handled without crashing the pipeline")
def step_then_no_crash(context):
    # Reaching this step proves the consumer loop did not raise.
    # consumer_errors contains the caught exception from the malformed message;
    # having at least one confirms the bad message was processed (not silently
    # dropped at the Kafka level) and that the consumer continued afterwards.
    assert len(context.consumer_errors) >= 1, (
        "Expected at least one gracefully-handled error from the malformed message, "
        f"got none. consumer_errors={context.consumer_errors}"
    )
