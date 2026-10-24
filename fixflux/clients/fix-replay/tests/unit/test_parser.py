import pytest

from fix_replay.parser import InvalidLine, ReplayOrder, load_files, parse_order

BUY = "8=FIX.4.2|35=D|49=C1|55=AAPL|54=1|40=2|44=175.50|38=100|"


class TestParseOrder:
    def test_parses_pipe_delimited_new_order_single(self):
        assert parse_order(BUY, "f:1") == ReplayOrder(
            source="f:1",
            client_id="C1",
            symbol="AAPL",
            side="BUY",
            price=175.5,
            quantity=100,
        )

    def test_parses_soh_delimited(self):
        order = parse_order(BUY.replace("|", "\x01"), "f:1")
        assert order is not None and order.side == "BUY"

    def test_missing_client_defaults_to_unknown(self):
        order = parse_order("35=D|55=AAPL|54=2|44=1|38=1", "f:1")
        assert order is not None
        assert order.client_id == "UNKNOWN"
        assert order.side == "SELL"

    @pytest.mark.parametrize("msg_type", ["A", "0", "1", "5"])
    def test_session_messages_return_none(self, msg_type):
        assert parse_order(f"8=FIX.4.2|35={msg_type}|49=C1|", "f:1") is None

    @pytest.mark.parametrize(
        "raw, error",
        [
            ("35=D|55=AAPL|54=1|44=1", "missing required tag"),
            ("35=G|55=AAPL|54=1|44=1|38=1", "unsupported message type"),
            ("35=D|55=AAPL|54=9|44=1|38=1", "unknown side"),
            ("35=D|55=AAPL|54=1|44=abc|38=1", "non-numeric"),
            ("35=D|55=AAPL|54=1|44=0|38=1", "must be positive"),
            ("35=D|55=AAPL|54=1|44=1|38=-5", "must be positive"),
        ],
    )
    def test_invalid_lines_raise(self, raw, error):
        with pytest.raises(InvalidLine, match=error):
            parse_order(raw, "f:1")


class TestLoadFiles:
    def test_keeps_file_and_line_order_and_classifies_lines(self, tmp_path):
        a = tmp_path / "a.txt"
        lines = ["# comment", "", "8=FIX.4.2|35=A|49=C1|", BUY, "35=D|55=AAPL|54=1|"]
        a.write_text("\n".join(lines) + "\n")
        b = tmp_path / "b.txt"
        b.write_text("35=D|49=C2|55=EURUSD|54=2|44=1.085|38=10\n")

        parsed = load_files([a, b])

        assert [o.source for o in parsed.orders] == ["a.txt:4", "b.txt:1"]
        assert parsed.session_messages == 1
        assert parsed.invalid == [
            {
                "source": "a.txt:5",
                "raw": "35=D|55=AAPL|54=1|",
                "error": "missing required tag(s): 44, 38",
            }
        ]
