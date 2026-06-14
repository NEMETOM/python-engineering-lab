from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from risk_service.models import (
    RejectedOrderEvent,
    RiskDecision,
    TradeEvent,
    ValidatedOrder,
)


def _now():
    return datetime.now(timezone.utc)


class TestValidatedOrder:
    def test_valid_construction(self):
        order = ValidatedOrder(
            order_id="O1",
            symbol="AAPL",
            side="BUY",
            price=100.0,
            quantity=10,
            timestamp=_now(),
        )
        assert order.order_id == "O1"
        assert order.symbol == "AAPL"

    def test_default_client_id_is_unknown(self):
        order = ValidatedOrder(
            order_id="O1",
            symbol="AAPL",
            side="BUY",
            price=100.0,
            quantity=10,
            timestamp=_now(),
        )
        assert order.client_id == "UNKNOWN"

    def test_explicit_client_id_is_stored(self):
        order = ValidatedOrder(
            order_id="O1",
            symbol="AAPL",
            side="BUY",
            price=100.0,
            quantity=10,
            timestamp=_now(),
            client_id="FIRM_A",
        )
        assert order.client_id == "FIRM_A"

    def test_invalid_side_raises(self):
        with pytest.raises(ValidationError):
            ValidatedOrder(
                order_id="O1",
                symbol="AAPL",
                side="HOLD",
                price=100.0,
                quantity=10,
                timestamp=_now(),
            )

    def test_missing_order_id_raises(self):
        with pytest.raises(ValidationError):
            ValidatedOrder(
                symbol="AAPL",
                side="BUY",
                price=100.0,
                quantity=10,
                timestamp=_now(),
            )


class TestRiskDecision:
    def test_approved_has_no_reason(self):
        d = RiskDecision(approved=True)
        assert d.approved is True
        assert d.reason is None

    def test_rejected_carries_reason(self):
        d = RiskDecision(approved=False, reason="notional exceeded")
        assert d.approved is False
        assert d.reason == "notional exceeded"

    def test_approved_with_explicit_none_reason(self):
        d = RiskDecision(approved=True, reason=None)
        assert d.reason is None


class TestTradeEvent:
    def test_valid_construction(self):
        trade = TradeEvent(
            trade_id="T1",
            symbol="AAPL",
            buy_order_id="B1",
            sell_order_id="S1",
            price=100.0,
            quantity=50,
        )
        assert trade.trade_id == "T1"
        assert trade.buy_order_id == "B1"
        assert trade.sell_order_id == "S1"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            TradeEvent(
                trade_id="T1",
                symbol="AAPL",
                buy_order_id="B1",
                price=100.0,
                quantity=50,
            )


class TestRejectedOrderEvent:
    def test_valid_construction(self):
        event = RejectedOrderEvent(
            order_id="O1",
            client_id="FIRM_A",
            symbol="AAPL",
            side="SELL",
            price=99.0,
            quantity=5,
            reason="notional exceeded",
            timestamp=_now(),
        )
        assert event.reason == "notional exceeded"
        assert event.client_id == "FIRM_A"
