#fix-protocol-simulator/tests/test_parser.py

from fix_simulator.protocol.fix_parser import FixParser


def test_serialize_fix_message():
    from fix_simulator.protocol.fix_message import FixMessage
    msg = FixMessage({"35": "D", "49": "CLIENT"})
    serialized = FixParser.serialize(msg)
    assert "35=D" in serialized
    assert serialized.endswith("\x01")


def test_parse_valid_fix_message():

    raw = "35=D\x0149=CLIENT\x0156=EXCHANGE\x01"

    msg = FixParser.parse(raw)

    assert msg.get("35") == "D"
    assert msg.get("49") == "CLIENT"