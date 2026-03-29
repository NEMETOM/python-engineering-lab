# fix-protocol-simulator/tests/bdd/steps/fix_message_steps.py

from behave import given, then, when  # type: ignore[import-untyped]
from fix_simulator.exchange.execution_reports import ExecutionReportFactory
from fix_simulator.protocol.fix_constants import (
    MSG_TYPE,
    NEW_ORDER_SINGLE,
    SENDER_COMP_ID,
)
from fix_simulator.protocol.fix_message import FixMessage
from fix_simulator.protocol.fix_parser import FixParser


@given("a FIX message with type {msg_type} and fields {fields}")
def given_fix_message(context, msg_type, fields):
    extra = {}
    for pair in fields.split("|"):
        tag, value = pair.split("=")
        extra[tag.strip()] = value.strip()
    context.message = FixMessage(
        {MSG_TYPE: msg_type, SENDER_COMP_ID: "CLIENT", **extra}
    )


@when("the message is parsed")
def when_message_parsed(context):
    raw = FixParser.serialize(context.message)
    context.parsed = FixParser.parse(raw)


@then("the parsed message type should be {msg_type}")
def then_parsed_msg_type(context, msg_type):
    assert context.parsed.get(MSG_TYPE) == msg_type


@given("a NewOrderSingle message for symbol {symbol} price {price} quantity {qty}")
def given_new_order_single(context, symbol, price, qty):
    context.message = FixMessage(
        {
            MSG_TYPE: NEW_ORDER_SINGLE,
            SENDER_COMP_ID: "CLIENT",
            "55": symbol,
            "44": price,
            "38": qty,
            "54": "1",
        }
    )


@given("an ExecutionReport for order {order_id} with status {status}")
def given_execution_report(context, order_id, status):
    context.message = ExecutionReportFactory.create(order_id, status)


@when("the message is serialized and parsed back")
def when_serialized_and_parsed(context):
    raw = FixParser.serialize(context.message)
    context.parsed = FixParser.parse(raw)


@then("the round-trip message type should be {msg_type}")
def then_roundtrip_msg_type(context, msg_type):
    assert context.parsed.get(MSG_TYPE) == msg_type


@then("the round-trip symbol should be {symbol}")
def then_roundtrip_symbol(context, symbol):
    assert context.parsed.get("55") == symbol


@then("the round-trip order id should be {order_id}")
def then_roundtrip_order_id(context, order_id):
    assert context.parsed.get("37") == order_id
