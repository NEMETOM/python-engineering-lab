# fix-protocol-simulator/tests/test_fix_message.py

from fix_simulator.protocol.fix_message import FixMessage


def test_get_existing_tag():
    msg = FixMessage({"35": "D", "49": "CLIENT"})
    assert msg.get("35") == "D"


def test_get_missing_tag_returns_none():
    msg = FixMessage({"35": "D"})
    assert msg.get("99") is None


def test_set_tag():
    msg = FixMessage({})
    msg.set("35", "D")
    assert msg.get("35") == "D"


def test_encode_produces_soh_delimited_string():
    msg = FixMessage({"35": "D", "49": "CLIENT"})
    encoded = msg.encode()
    assert "35=D" in encoded
    assert "49=CLIENT" in encoded
    assert encoded.endswith("\x01")


def test_encode_fields_separated_by_soh():
    msg = FixMessage({"35": "D", "49": "CLIENT"})
    encoded = msg.encode()
    assert "\x01" in encoded
