# fix-protocol-simulator/tests/test_parser.py

import pytest
from fix_simulator.protocol.fix_constants import (
    EXECUTION_REPORT,
    HEARTBEAT,
    LOGON,
    MSG_TYPE,
    NEW_ORDER_SINGLE,
    ORDER_CANCEL,
    SENDER_COMP_ID,
    TARGET_COMP_ID,
)
from fix_simulator.protocol.fix_message import FixMessage
from fix_simulator.protocol.fix_parser import FixParser


def test_serialize_fix_message():
    msg = FixMessage({"35": "D", "49": "CLIENT"})
    serialized = FixParser.serialize(msg)
    assert "35=D" in serialized
    assert serialized.endswith("\x01")


def test_parse_valid_fix_message():
    raw = "35=D\x0149=CLIENT\x0156=EXCHANGE\x01"
    msg = FixParser.parse(raw)
    assert msg.get("35") == "D"
    assert msg.get("49") == "CLIENT"


@pytest.mark.parametrize(
    "msg_type, extra_fields",
    [
        (LOGON, {"108": "30"}),
        (HEARTBEAT, {"112": "TEST"}),
        (NEW_ORDER_SINGLE, {"55": "AAPL", "44": "100", "38": "10", "54": "1"}),
        (EXECUTION_REPORT, {"37": "ORD001", "39": "2"}),
        (ORDER_CANCEL, {"41": "ORD001", "55": "AAPL"}),
    ],
)
def test_parse_message_types(msg_type, extra_fields):
    fields = {
        MSG_TYPE: msg_type,
        SENDER_COMP_ID: "CLIENT",
        TARGET_COMP_ID: "EXCHANGE",
        **extra_fields,
    }
    raw = FixParser.serialize(FixMessage(fields))
    parsed = FixParser.parse(raw)
    assert parsed.get(MSG_TYPE) == msg_type
    for tag, value in extra_fields.items():
        assert parsed.get(tag) == value


def test_parse_ignores_incomplete_parts():
    raw = "35=A\x01no_equals_sign\x0149=CLIENT\x01"
    msg = FixParser.parse(raw)
    assert msg.get("35") == "A"
    assert msg.get("49") == "CLIENT"


def test_serialize_roundtrip():
    fields = {MSG_TYPE: NEW_ORDER_SINGLE, SENDER_COMP_ID: "CLIENT", "55": "AAPL"}
    msg = FixMessage(fields)
    parsed = FixParser.parse(FixParser.serialize(msg))
    assert parsed.get(MSG_TYPE) == NEW_ORDER_SINGLE
    assert parsed.get("55") == "AAPL"
