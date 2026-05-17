from datetime import datetime

import pytest
from pydantic import ValidationError as PydanticValidationError
from shared.schemas.book_event import BookEvent


class TestBookEventDefaults:
    def test_only_symbol_required(self):
        event = BookEvent(symbol="AAPL")
        assert event.symbol == "AAPL"

    def test_best_bid_defaults_to_none(self):
        assert BookEvent(symbol="AAPL").best_bid is None

    def test_best_ask_defaults_to_none(self):
        assert BookEvent(symbol="AAPL").best_ask is None

    def test_mid_price_defaults_to_none(self):
        assert BookEvent(symbol="AAPL").mid_price is None

    def test_last_trade_price_defaults_to_none(self):
        assert BookEvent(symbol="AAPL").last_trade_price is None

    def test_timestamp_defaults_to_now(self):
        event = BookEvent(symbol="AAPL")
        assert isinstance(event.timestamp, datetime)

    def test_symbol_is_required(self):
        with pytest.raises(PydanticValidationError):
            BookEvent()


class TestBookEventWithOptionalFields:
    def test_best_bid_and_ask_accepted(self):
        event = BookEvent(symbol="AAPL", best_bid=99.5, best_ask=100.0)
        assert event.best_bid == 99.5
        assert event.best_ask == 100.0

    def test_mid_price_accepted(self):
        event = BookEvent(symbol="AAPL", mid_price=99.75)
        assert event.mid_price == 99.75

    def test_last_trade_price_accepted(self):
        event = BookEvent(symbol="AAPL", last_trade_price=99.8)
        assert event.last_trade_price == 99.8

    def test_all_optional_fields_accepted(self):
        event = BookEvent(
            symbol="BTCUSD",
            best_bid=49900.0,
            best_ask=50100.0,
            mid_price=50000.0,
            last_trade_price=49950.0,
        )
        assert event.best_bid == 49900.0
        assert event.best_ask == 50100.0
        assert event.mid_price == 50000.0
        assert event.last_trade_price == 49950.0

    @pytest.mark.parametrize("symbol", ["AAPL", "BTCUSD", "EURUSD"])
    def test_various_symbols_accepted(self, symbol):
        event = BookEvent(symbol=symbol)
        assert event.symbol == symbol
