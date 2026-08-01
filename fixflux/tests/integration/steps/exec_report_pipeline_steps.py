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


def _poll_for_exec_report(context, order_id, exec_type, timeout_secs):
    """Poll context.exec_reports_consumer until a matching report arrives or timeout.

    A single poll() batch often contains reports for *other* order_ids/exec_types
    this scenario will check later (e.g. both sides' Fill reports land together).
    Kafka consumption is destructive - a message not matched now is gone from the
    topic's read position forever - so every non-matching message is buffered on
    context.exec_reports_buffer for a subsequent call to check first.
    """
    for i, value in enumerate(context.exec_reports_buffer):
        if value.get("order_id") == order_id and value.get("exec_type") == exec_type:
            del context.exec_reports_buffer[i]
            return value

    deadline = time.monotonic() + timeout_secs
    while time.monotonic() < deadline:
        records = context.exec_reports_consumer.poll(timeout_ms=2_000)
        for tp_records in records.values():
            for msg in tp_records:
                value = msg.value
                if (
                    value.get("order_id") == order_id
                    and value.get("exec_type") == exec_type
                ):
                    return value
                context.exec_reports_buffer.append(value)
    return None


# ── Crossing order setup (Fill scenario) ──────────────────────────────────────


@given(
    'a crossing buy order for the test client symbol "{symbol}" at price {price:f} qty {qty:d}'
)
def step_crossing_buy_order(context, symbol, price, qty):
    # matching-engine's order books are in-memory and never cleared between
    # runs; a fixed symbol would let a resting order from an earlier/failed
    # run silently steal this scenario's match. Suffix it unique per run.
    context.risk_crossing_symbol = f"{symbol}-{uuid.uuid4().hex[:8].upper()}"
    context.risk_buy_order_id = f"ORD-{uuid.uuid4().hex[:12]}"
    context.risk_buy_payload = _build_order_payload(
        order_id=context.risk_buy_order_id,
        client_id=context.risk_client_id,
        symbol=context.risk_crossing_symbol,
        side="BUY",
        price=price,
        quantity=qty,
    )


@given(
    'a crossing sell order for the second test client symbol "{symbol}" at price {price:f} qty {qty:d}'
)
def step_crossing_sell_order(context, symbol, price, qty):
    context.risk_sell_order_id = f"ORD-{uuid.uuid4().hex[:12]}"
    context.risk_sell_payload = _build_order_payload(
        order_id=context.risk_sell_order_id,
        client_id=context.risk_client_id_2,
        symbol=context.risk_crossing_symbol,
        side="SELL",
        price=price,
        quantity=qty,
    )


@when("both crossing orders are published to validated_orders")
def step_publish_crossing_orders(context):
    _publish("validated_orders", context.risk_buy_payload)
    _publish("validated_orders", context.risk_sell_payload)


# ── Assertions ────────────────────────────────────────────────────────────────


@then(
    'an execution report for the order with ExecType "{exec_type}" appears within {timeout:d} seconds'
)
def step_assert_exec_report(context, exec_type, timeout):
    result = _poll_for_exec_report(context, context.risk_order_id, exec_type, timeout)
    assert result is not None, (
        f"No execution report with ExecType={exec_type!r} for order {context.risk_order_id} "
        f"appeared in execution_reports within {timeout}s.\n"
        "Is risk-service running?  docker compose --profile full up"
    )
    context.last_exec_report = result


@then('the execution report OrdStatus is "{ord_status}"')
def step_assert_ord_status(context, ord_status):
    assert (
        context.last_exec_report["ord_status"] == ord_status
    ), f"OrdStatus: expected {ord_status!r}, got {context.last_exec_report['ord_status']!r}"


@then('the execution report reason contains "{fragment}"')
def step_assert_exec_report_reason(context, fragment):
    reason = context.last_exec_report.get("reason") or ""
    assert (
        fragment in reason
    ), f"Expected exec report reason to contain {fragment!r}, got: {reason!r}"


@then("a Fill execution report for the buy order appears within {timeout:d} seconds")
def step_assert_buy_fill(context, timeout):
    result = _poll_for_exec_report(context, context.risk_buy_order_id, "F", timeout)
    assert result is not None, (
        f"No Fill execution report for buy order {context.risk_buy_order_id} appeared "
        f"within {timeout}s.\n"
        "Is matching-engine running?  docker compose --profile full up"
    )
    context.buy_fill_report = result


@then("a Fill execution report for the sell order appears within {timeout:d} seconds")
def step_assert_sell_fill(context, timeout):
    result = _poll_for_exec_report(context, context.risk_sell_order_id, "F", timeout)
    assert result is not None, (
        f"No Fill execution report for sell order {context.risk_sell_order_id} appeared "
        f"within {timeout}s.\n"
        "Is matching-engine running?  docker compose --profile full up"
    )
    context.sell_fill_report = result


@then("the buy Fill execution report has client_id matching the test client")
def step_assert_buy_fill_client_id(context):
    assert context.buy_fill_report["client_id"] == context.risk_client_id, (
        f"client_id: expected {context.risk_client_id!r}, "
        f"got {context.buy_fill_report['client_id']!r}"
    )


@then("the sell Fill execution report has client_id matching the second test client")
def step_assert_sell_fill_client_id(context):
    assert context.sell_fill_report["client_id"] == context.risk_client_id_2, (
        f"client_id: expected {context.risk_client_id_2!r}, "
        f"got {context.sell_fill_report['client_id']!r}"
    )
