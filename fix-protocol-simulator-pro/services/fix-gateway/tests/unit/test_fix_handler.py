# fix-protocol-simulator-pro/services/fix-gateway/tests/unit/test_fix_handler.py

from fix_gateway.fix_handler import FixHandler


def test_parse_new_order():

    handler = FixHandler()

    raw = "35=D|55=BTCUSD|54=1|44=50000|38=1|"

    msg = handler.parse(raw)

    assert msg["35"] == "D"

    assert msg["55"] == "BTCUSD"


def test_identify_logon():

    handler = FixHandler()

    msg = {"35": "A"}

    assert handler.is_logon(msg)


def test_identify_heartbeat():

    handler = FixHandler()

    assert handler.is_heartbeat({"35": "0"})
    assert not handler.is_heartbeat({"35": "A"})


def test_identify_new_order():

    handler = FixHandler()

    assert handler.is_new_order({"35": "D"})
    assert not handler.is_new_order({"35": "A"})


def test_parse_ignores_malformed_fields():

    handler = FixHandler()

    raw = "35=D|BADFIELD|55=BTCUSD|"

    msg = handler.parse(raw)

    assert msg["35"] == "D"
    assert msg["55"] == "BTCUSD"
    assert "BADFIELD" not in msg


def test_parse_empty_message():

    handler = FixHandler()

    msg = handler.parse("")

    assert msg == {}


def test_custom_delimiter():

    handler = FixHandler(delimiter="\x01")

    raw = "35=D\x0155=ETHUSD\x0154=1\x01"

    msg = handler.parse(raw)

    assert msg["35"] == "D"
    assert msg["55"] == "ETHUSD"
