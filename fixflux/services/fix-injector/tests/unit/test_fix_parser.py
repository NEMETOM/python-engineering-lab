import pytest

from fix_injector.fix_parser import (
    FixParseError,
    parse_new_order_single,
    to_raw_order_event,
)


def test_parses_pipe_delimited_new_order_single():
    raw = "8=FIX.4.2|35=D|49=CLIENT1|11=ORD1|55=EURUSD|54=1|40=2|44=1.09000|38=100|"

    parsed = parse_new_order_single(raw)

    assert parsed["symbol"] == "EURUSD"
    assert parsed["side"] == "BUY"
    assert parsed["price"] == pytest.approx(1.09)
    assert parsed["quantity"] == 100
    assert parsed["client_id"] == "CLIENT1"
    assert parsed["client_order_id"] == "ORD1"


def test_parses_soh_delimited_new_order_single():
    raw = "8=FIX.4.2\x0135=D\x0149=CLIENT1\x0155=AAPL\x0154=2\x0144=175.00\x0138=50\x01"

    parsed = parse_new_order_single(raw)

    assert parsed["symbol"] == "AAPL"
    assert parsed["side"] == "SELL"
    assert parsed["quantity"] == 50


def test_defaults_missing_client_id_to_unknown():
    raw = "8=FIX.4.2|35=D|55=EURUSD|54=1|44=1.09000|38=100|"

    parsed = parse_new_order_single(raw)

    assert parsed["client_id"] == "UNKNOWN"


@pytest.mark.parametrize(
    "raw",
    [
        "8=FIX.4.2|35=A|49=CLIENT1|",
        "NOT_A_FIX_MESSAGE",
        "8=FIX.4.2|35=D|49=CLIENT1|55=EURUSD|54=1|44=1.09000|",
        "8=FIX.4.2|35=D|49=CLIENT1|55=EURUSD|54=9|44=1.09000|38=100|",
        "8=FIX.4.2|35=D|49=CLIENT1|55=EURUSD|54=1|44=oops|38=100|",
    ],
)
def test_rejects_invalid_messages(raw):
    with pytest.raises(FixParseError):
        parse_new_order_single(raw)


def test_to_raw_order_event_matches_order_service_schema():
    parsed = parse_new_order_single(
        "8=FIX.4.2|35=D|49=CLIENT1|55=EURUSD|54=1|44=1.09000|38=100|"
    )

    event = to_raw_order_event(parsed)

    assert set(event) == {
        "symbol",
        "side",
        "price",
        "quantity",
        "timestamp",
        "client_id",
    }
    assert event["symbol"] == "EURUSD"
    assert event["side"] == "BUY"
