import json
import os
import time
import uuid
from datetime import datetime, timezone

import httpx
from behave import given, then, when

_COMPLIANCE_URL = os.getenv("COMPLIANCE_URL", "http://localhost:8010")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_order_payload(client_id, symbol, side, price, quantity):
    return {
        "order_id": f"ORD-{uuid.uuid4().hex[:12]}",
        "client_id": client_id,
        "symbol": symbol,
        "side": side,
        "price": float(price),
        "quantity": int(quantity),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _publish(topic, payload):
    from kafka import KafkaProducer

    broker = os.getenv("KAFKA_BROKER", "localhost:9092")
    producer = KafkaProducer(
        bootstrap_servers=broker,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    producer.send(topic, payload)
    producer.flush()
    producer.close()


def _poll_for_violation(client_id, rule_name, timeout_secs):
    deadline = time.monotonic() + timeout_secs
    while time.monotonic() < deadline:
        try:
            response = httpx.get(
                f"{_COMPLIANCE_URL}/violations",
                params={"client_id": client_id, "rule_name": rule_name, "limit": 10},
                timeout=5.0,
            )
            if response.status_code == 200 and response.json():
                return response.json()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    return None


def _poll_for_high_risk(client_id, timeout_secs):
    deadline = time.monotonic() + timeout_secs
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{_COMPLIANCE_URL}/risk/{client_id}", timeout=5.0)
            if response.status_code == 200 and response.json().get("is_high_risk"):
                return response.json()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    return None


def _poll_for_audit_entry(client_id, event_type, timeout_secs):
    deadline = time.monotonic() + timeout_secs
    while time.monotonic() < deadline:
        try:
            response = httpx.get(
                f"{_COMPLIANCE_URL}/audit",
                params={"client_id": client_id, "event_type": event_type, "limit": 10},
                timeout=5.0,
            )
            if response.status_code == 200 and response.json():
                return response.json()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    return None


# ── Client setup ──────────────────────────────────────────────────────────────


@given("a unique compliance test client is created")
def step_create_compliance_client(context):
    context.compliance_client_id = f"COMPTEST-{uuid.uuid4().hex[:8].upper()}"


# ── PriceDeviationRule ────────────────────────────────────────────────────────


@given(
    'a price baseline of {baseline_price:f} has been established for symbol "{symbol}" on raw_orders'
)
def step_price_baseline(context, baseline_price, symbol):
    payload = _build_order_payload(
        context.compliance_client_id, symbol, "BUY", baseline_price, 10
    )
    _publish("raw_orders", payload)
    time.sleep(2)  # let the compliance-raw consumer thread record the history


@when(
    'an order for the test client symbol "{symbol}" price {price:f} qty {qty:d} is published to raw_orders'
)
def step_publish_raw_order(context, symbol, price, qty):
    payload = _build_order_payload(
        context.compliance_client_id, symbol, "BUY", price, qty
    )
    _publish("raw_orders", payload)


# ── RapidFireRule ─────────────────────────────────────────────────────────────


@when(
    '11 orders for the test client symbol "{symbol}" are rapidly published to validated_orders'
)
def step_rapid_fire_burst(context, symbol):
    for _ in range(11):
        payload = _build_order_payload(
            context.compliance_client_id, symbol, "BUY", 100.00, 10
        )
        _publish("validated_orders", payload)


# ── VolumeSpikeRule ───────────────────────────────────────────────────────────


@given(
    'a volume baseline of qty {baseline_qty:d} has been established for symbol "{symbol}" on validated_orders'
)
def step_volume_baseline(context, baseline_qty, symbol):
    payload = _build_order_payload(
        context.compliance_client_id, symbol, "BUY", 100.00, baseline_qty
    )
    _publish("validated_orders", payload)
    time.sleep(2)  # let the compliance-validated consumer thread record the baseline


@when(
    'an order for the test client symbol "{symbol}" qty {qty:d} is published to validated_orders'
)
def step_publish_validated_order(context, symbol, qty):
    payload = _build_order_payload(
        context.compliance_client_id, symbol, "BUY", 100.00, qty
    )
    _publish("validated_orders", payload)


# ── RepeatedOrdersRule ────────────────────────────────────────────────────────


@when(
    'an identical order for the test client symbol "{symbol}" side "{side}" '
    "price {price:f} qty {qty:d} is published to validated_orders {count:d} times"
)
def step_publish_identical_orders(context, symbol, side, price, qty, count):
    for _ in range(count):
        payload = _build_order_payload(
            context.compliance_client_id, symbol, side, price, qty
        )
        _publish("validated_orders", payload)


# ── Wash trading / risk scoring ───────────────────────────────────────────────


@when('the test client wash-trades symbol "{symbol}" via validated_orders')
def step_wash_trade(context, symbol):
    buy = _build_order_payload(context.compliance_client_id, symbol, "BUY", 100.00, 10)
    _publish("validated_orders", buy)
    time.sleep(1)
    sell = _build_order_payload(
        context.compliance_client_id, symbol, "SELL", 100.00, 10
    )
    _publish("validated_orders", sell)


# ── Audit trail ───────────────────────────────────────────────────────────────


@when(
    'a clean order for the test client symbol "{symbol}" price {price:f} qty {qty:d} is published to raw_orders'
)
def step_publish_clean_order(context, symbol, price, qty):
    payload = _build_order_payload(
        context.compliance_client_id, symbol, "BUY", price, qty
    )
    _publish("raw_orders", payload)


@when(
    'an order for the test client symbol "{symbol}" price {price:f} qty {qty:d} is published to raw_orders twice'
)
def step_publish_duplicate_orders(context, symbol, price, qty):
    for _ in range(2):
        payload = _build_order_payload(
            context.compliance_client_id, symbol, "BUY", price, qty
        )
        _publish("raw_orders", payload)


# ── Assertions ────────────────────────────────────────────────────────────────


@then(
    'a compliance violation for rule "{rule}" for the test client appears within {timeout:d} seconds'
)
def step_assert_compliance_violation(context, rule, timeout):
    result = _poll_for_violation(context.compliance_client_id, rule, timeout)
    assert result is not None, (
        f"No {rule} violation for client {context.compliance_client_id} appeared "
        f"within {timeout}s.\n"
        "Is compliance-consumer running?  docker compose --profile full up"
    )


@then("the test client is flagged high-risk in GET /risk within {timeout:d} seconds")
def step_assert_high_risk(context, timeout):
    result = _poll_for_high_risk(context.compliance_client_id, timeout)
    assert result is not None, (
        f"Client {context.compliance_client_id} was not flagged high-risk within "
        f"{timeout}s.\n"
        "Is compliance-consumer running?  docker compose --profile full up"
    )


@then(
    'the "{event_type}" audit entry for the test client appears within {timeout:d} seconds'
)
def step_assert_audit_entry(context, event_type, timeout):
    result = _poll_for_audit_entry(context.compliance_client_id, event_type, timeout)
    assert result is not None, (
        f"No {event_type!r} audit entry for client {context.compliance_client_id} "
        f"appeared within {timeout}s.\n"
        "Is compliance-consumer running?  docker compose --profile full up"
    )
