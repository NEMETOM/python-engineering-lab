from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from reporting_service.schemas import RegulatoryTradeReport, TradeEvent

VALID_LEI = "506700GE1G29325QX363"


def _make_report(**overrides):
    defaults = {
        "trade_id": "T1",
        "symbol": "AAPL",
        "price": 175.5,
        "price_currency": "USD",
        "quantity": 100,
        "trading_timestamp": datetime(2026, 10, 25, 12, 0, tzinfo=UTC),
        "reporting_timestamp": datetime(2026, 10, 25, 12, 0, 1, tzinfo=UTC),
        "buyer_client_id": "BUYER",
        "seller_client_id": "SELLER",
        "buyer_lei": VALID_LEI,
        "seller_lei": VALID_LEI,
        "buyer_trading_capacity": "DEAL",
        "seller_trading_capacity": "DEAL",
        "cfi_code": "ESVUFR",
        "asset_class": "EQUITY",
        "status": "REPORTABLE",
        "status_reason": None,
        "publication_latency_ms": 1000,
        "deadline_breached": False,
    }
    return RegulatoryTradeReport(**{**defaults, **overrides})


def _make_trade_payload(**overrides):
    defaults = {
        "trade_id": "T1",
        "symbol": "AAPL",
        "buy_order_id": "B1",
        "sell_order_id": "S1",
        "price": 175.5,
        "quantity": 100,
    }
    return {**defaults, **overrides}


class TestRegulatoryTradeReport:
    def test_valid_report_is_accepted(self):
        assert _make_report().status == "REPORTABLE"

    @pytest.mark.parametrize(
        "field, value",
        [
            ("buyer_lei", "506700GE1G29325QX364"),  # bad checksum
            ("seller_lei", "ABC123"),  # the draft spec's 10-char format
            ("cfi_code", "ESVU"),  # the draft spec's 4-char format
            ("cfi_code", "esvufr"),
            ("buyer_trading_capacity", "MATCH"),  # not an RTS 22 code
            ("seller_trading_capacity", "AENE"),
            ("status", "SENT"),
        ],
    )
    def test_rejects_non_regulatory_formats(self, field, value):
        with pytest.raises(ValidationError):
            _make_report(**{field: value})

    @pytest.mark.parametrize(
        "field",
        [
            "trading_timestamp",
            "price_currency",
            "buyer_lei",
            "seller_lei",
            "buyer_trading_capacity",
            "seller_trading_capacity",
            "cfi_code",
        ],
    )
    def test_reportable_requires_every_regulatory_field(self, field):
        with pytest.raises(ValidationError, match=field):
            _make_report(**{field: None})

    def test_incomplete_report_may_lack_regulatory_fields(self):
        report = _make_report(
            status="INCOMPLETE", status_reason="x", buyer_lei=None, cfi_code=None
        )
        assert report.buyer_lei is None


class TestTradeEvent:
    def test_parses_payload_without_new_optional_fields(self):
        # Trades from a matching-engine build predating reporting-service.
        trade = TradeEvent(**_make_trade_payload())
        assert trade.buy_client_id == "UNKNOWN"
        assert trade.timestamp is None

    def test_ignores_trace_context_fields(self):
        trade = TradeEvent(**_make_trade_payload(_trace_id="abc", _span_id="def"))
        assert trade.trade_id == "T1"

    @pytest.mark.parametrize("field, value", [("price", 0), ("quantity", -1)])
    def test_rejects_non_positive_price_or_quantity(self, field, value):
        with pytest.raises(ValidationError):
            TradeEvent(**_make_trade_payload(**{field: value}))
