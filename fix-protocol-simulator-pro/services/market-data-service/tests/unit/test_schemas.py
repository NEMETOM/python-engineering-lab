from datetime import datetime, timezone

import pytest
from market_data_service.schemas.market_data_event import MarketDataEvent
from market_data_service.schemas.order_book_event import OrderBookEvent
from market_data_service.schemas.trade_event import TradeEvent
from pydantic import ValidationError

NOW = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestTradeEvent:

    def test_valid_trade_event(self):
        event = TradeEvent(symbol="AAPL", price=150.0, quantity=100, timestamp=NOW)
        assert event.symbol == "AAPL"
        assert event.price == 150.0
        assert event.quantity == 100
        assert event.timestamp == NOW

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(symbol="AAPL", price=150.0, timestamp=NOW)

    def test_invalid_price_type_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(symbol="AAPL", price="not-a-float", quantity=10, timestamp=NOW)


class TestOrderBookEvent:

    def test_valid_order_book_event(self):
        event = OrderBookEvent(
            symbol="AAPL", best_bid=99.50, best_ask=100.50, timestamp=NOW
        )
        assert event.symbol == "AAPL"
        assert event.best_bid == 99.50
        assert event.best_ask == 100.50
        assert event.timestamp == NOW

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            OrderBookEvent(symbol="AAPL", best_bid=99.50, timestamp=NOW)

    def test_invalid_best_bid_type_raises(self):
        with pytest.raises(ValidationError):
            OrderBookEvent(symbol="AAPL", best_bid="bad", best_ask=100.0, timestamp=NOW)


class TestMarketDataEvent:

    def test_valid_market_data_event_with_all_fields(self):
        event = MarketDataEvent(
            symbol="AAPL",
            best_bid=99.50,
            best_ask=100.50,
            mid_price=100.0,
            last_trade_price=99.75,
            timestamp=NOW,
        )
        assert event.symbol == "AAPL"
        assert event.best_bid == 99.50
        assert event.best_ask == 100.50
        assert event.mid_price == 100.0
        assert event.last_trade_price == 99.75

    def test_optional_fields_can_be_none(self):
        event = MarketDataEvent(
            symbol="AAPL",
            best_bid=None,
            best_ask=None,
            mid_price=None,
            last_trade_price=None,
            timestamp=NOW,
        )
        assert event.best_bid is None
        assert event.best_ask is None
        assert event.mid_price is None
        assert event.last_trade_price is None

    def test_missing_symbol_raises(self):
        with pytest.raises(ValidationError):
            MarketDataEvent(
                best_bid=99.50,
                best_ask=100.50,
                mid_price=100.0,
                last_trade_price=99.75,
                timestamp=NOW,
            )
