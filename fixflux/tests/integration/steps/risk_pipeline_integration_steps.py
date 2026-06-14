import json
import os
import time
import uuid
from datetime import datetime, timezone

from behave import given, then, when


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_order_payload(order_id, client_id, symbol, side, price, quantity):
    return {
        "order_id": order_id,
        "client_id": client_id,
        "symbol": symbol,
        "side": side,
        "price": float(price),
        "quantity": int(quantity),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _make_producer():
    from kafka import KafkaProducer

    broker = os.getenv("KAFKA_BROKER", "localhost:9092")
    return KafkaProducer(
        bootstrap_servers=broker,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def _publish(topic, payload):
    producer = _make_producer()
    producer.send(topic, payload)
    producer.flush()
    producer.close()


def _poll_for_order_id(consumer, order_id, timeout_secs):
    """Poll consumer until a message with the given order_id arrives or timeout."""
    deadline = time.monotonic() + timeout_secs
    while time.monotonic() < deadline:
        records = consumer.poll(timeout_ms=2_000)
        for tp_records in records.values():
            for msg in tp_records:
                if msg.value.get("order_id") == order_id:
                    return msg.value
    return None


# ── Context setup ─────────────────────────────────────────────────────────────


@given("a unique risk test client is created")
def step_create_unique_client(context):
    context.risk_client_id = f"RSKTEST-{uuid.uuid4().hex[:8]}"


@given("a second unique risk test client is created")
def step_create_second_unique_client(context):
    context.risk_client_id_2 = f"RSKTEST-{uuid.uuid4().hex[:8]}"


# ── Order creation ────────────────────────────────────────────────────────────


@given(
    'a validated order for the test client symbol "{symbol}" side "{side}" '
    "price {price:f} qty {qty:d}"
)
def step_order_test_client(context, symbol, side, price, qty):
    context.risk_order_id = f"ORD-{uuid.uuid4().hex[:12]}"
    context.risk_order_payload = _build_order_payload(
        order_id=context.risk_order_id,
        client_id=context.risk_client_id,
        symbol=symbol,
        side=side,
        price=price,
        quantity=qty,
    )


@given(
    'a validated order for the second test client symbol "{symbol}" side "{side}" '
    "price {price:f} qty {qty:d}"
)
def step_order_second_client(context, symbol, side, price, qty):
    context.risk_order_id = f"ORD-{uuid.uuid4().hex[:12]}"
    context.risk_order_payload = _build_order_payload(
        order_id=context.risk_order_id,
        client_id=context.risk_client_id_2,
        symbol=symbol,
        side=side,
        price=price,
        quantity=qty,
    )


# ── Reference price setup ─────────────────────────────────────────────────────


@given(
    'a trade for "{symbol}" at price {ref_price:f} has been processed by the risk service'
)
def step_establish_reference_price(context, symbol, ref_price):
    trade_payload = {
        "trade_id": f"TRD-{uuid.uuid4().hex[:12]}",
        "symbol": symbol,
        "buy_order_id": f"B-{uuid.uuid4().hex[:8]}",
        "sell_order_id": f"S-{uuid.uuid4().hex[:8]}",
        "price": float(ref_price),
        "quantity": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _publish("trades", trade_payload)
    # Allow the risk-service consumer loop to pick up the trade before the order arrives
    time.sleep(2)


# ── Open order count setup ────────────────────────────────────────────────────


@given(
    '{count:d} open orders for the test client on "{symbol}" have been approved '
    "by the risk service"
)
def step_build_open_order_count(context, count, symbol):
    """Publish `count` small orders and wait for them all to arrive in risk_approved_orders."""
    from kafka import KafkaConsumer, KafkaProducer

    broker = os.getenv("KAFKA_BROKER", "localhost:9092")

    temp_consumer = KafkaConsumer(
        "risk_approved_orders",
        bootstrap_servers=broker,
        group_id=f"int-setup-{uuid.uuid4().hex}",
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        consumer_timeout_ms=20_000,
        session_timeout_ms=10_000,
    )
    temp_consumer.poll(timeout_ms=2_000)

    producer = KafkaProducer(
        bootstrap_servers=broker,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    order_ids = set()
    for _ in range(count):
        oid = f"ORD-{uuid.uuid4().hex[:12]}"
        order_ids.add(oid)
        producer.send(
            "validated_orders",
            _build_order_payload(
                order_id=oid,
                client_id=context.risk_client_id,
                symbol=symbol,
                side="BUY",
                price=10.00,
                quantity=1,
            ),
        )
    producer.flush()
    producer.close()

    approved = set()
    deadline = time.monotonic() + 30
    while len(approved) < count and time.monotonic() < deadline:
        records = temp_consumer.poll(timeout_ms=2_000)
        for tp_records in records.values():
            for msg in tp_records:
                if msg.value.get("order_id") in order_ids:
                    approved.add(msg.value["order_id"])

    temp_consumer.close()

    assert len(approved) == count, (
        f"Expected {count} setup orders approved, got {len(approved)}. "
        "Is risk-service running?  docker compose --profile full up"
    )


# ── Publish ───────────────────────────────────────────────────────────────────


@when("the order is published to validated_orders")
def step_publish_order(context):
    _publish("validated_orders", context.risk_order_payload)


# ── Assertions ────────────────────────────────────────────────────────────────


@then("the order appears in risk_approved_orders within {timeout:d} seconds")
def step_assert_approved(context, timeout):
    result = _poll_for_order_id(
        context.risk_approved_consumer, context.risk_order_id, timeout
    )
    assert result is not None, (
        f"Order {context.risk_order_id} did not appear in risk_approved_orders "
        f"within {timeout}s.\n"
        "Is risk-service running?  docker compose --profile full up"
    )


@then("the order appears in risk_rejected_orders within {timeout:d} seconds")
def step_assert_rejected(context, timeout):
    result = _poll_for_order_id(
        context.risk_rejected_consumer, context.risk_order_id, timeout
    )
    assert result is not None, (
        f"Order {context.risk_order_id} did not appear in risk_rejected_orders "
        f"within {timeout}s.\n"
        "Is risk-service running?  docker compose --profile full up"
    )
    context.last_rejection = result


@then('the rejection reason contains "{fragment}"')
def step_assert_rejection_reason(context, fragment):
    reason = context.last_rejection.get("reason", "")
    assert fragment in reason, (
        f"Expected rejection reason to contain {fragment!r}, got: {reason!r}"
    )
