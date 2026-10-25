from datetime import UTC, datetime, timedelta

import pytest

from reporting_service.enricher import ReportEnricher
from reporting_service.schemas import TradeEvent

NOW = datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC)
BUYER_LEI = "SIMX00BUYER000000000"
SELLER_LEI = "SIMX00SELLER00000000"


def _lei(base18: str) -> str:
    """Append valid ISO 7064 check digits to an 18-character base."""
    n = int("".join(str(int(c, 36)) for c in base18 + "00"))
    return f"{base18}{98 - n % 97:02d}"


def _make_reference_data(**overrides):
    defaults = {
        "participants": {
            "BUYER": {"lei": _lei("SIMX00BUYER0000000"), "trading_capacity": "DEAL"},
            "SELLER": {"lei": _lei("SIMX00SELLER000000"), "trading_capacity": "MTCH"},
        },
        "instruments": {
            "AAPL": {
                "asset_class": "EQUITY",
                "cfi_code": "ESVUFR",
                "currency": "USD",
                "mifid_in_scope": True,
            },
            "EURUSD": {
                "asset_class": "FX_SPOT",
                "currency": "USD",
                "mifid_in_scope": False,
                "out_of_scope_reason": "FX spot out of scope",
            },
        },
    }
    return {**defaults, **overrides}


def _make_trade(**overrides):
    defaults = {
        "trade_id": "T1",
        "symbol": "AAPL",
        "buy_order_id": "B1",
        "sell_order_id": "S1",
        "price": 175.5,
        "quantity": 100,
        "buy_client_id": "BUYER",
        "sell_client_id": "SELLER",
        "timestamp": NOW - timedelta(milliseconds=250),
    }
    return TradeEvent(**{**defaults, **overrides})


def _make_enricher(reference_data=None, **kwargs):
    return ReportEnricher(
        reference_data or _make_reference_data(), clock=lambda: NOW, **kwargs
    )


class TestReportableTrades:
    def test_in_scope_trade_with_known_parties_is_reportable(self):
        report = _make_enricher().enrich(_make_trade())

        assert report.status == "REPORTABLE"
        assert report.status_reason is None
        assert report.buyer_lei == _lei("SIMX00BUYER0000000")
        assert report.seller_lei == _lei("SIMX00SELLER000000")
        assert report.buyer_trading_capacity == "DEAL"
        assert report.seller_trading_capacity == "MTCH"
        assert report.cfi_code == "ESVUFR"
        assert report.price_currency == "USD"
        assert report.reporting_timestamp == NOW

    def test_latency_is_execution_to_report_time(self):
        report = _make_enricher().enrich(_make_trade())
        assert report.publication_latency_ms == 250
        assert report.deadline_breached is False

    def test_naive_execution_timestamp_is_treated_as_utc(self):
        naive = (NOW - timedelta(seconds=2)).replace(tzinfo=None)
        report = _make_enricher().enrich(_make_trade(timestamp=naive))
        assert report.publication_latency_ms == 2000


class TestPublicationDeadline:
    @pytest.mark.parametrize(
        "seconds_ago, breached",
        [(59.9, False), (60.0, False), (60.001, True), (300, True)],
    )
    def test_breach_is_strictly_beyond_one_minute(self, seconds_ago, breached):
        trade = _make_trade(timestamp=NOW - timedelta(seconds=seconds_ago))
        assert _make_enricher().enrich(trade).deadline_breached is breached

    def test_deadline_is_configurable(self):
        trade = _make_trade(timestamp=NOW - timedelta(seconds=5))
        assert _make_enricher(deadline_seconds=1).enrich(trade).deadline_breached

    def test_late_trade_is_still_reportable(self):
        # A late report must still be filed; lateness is flagged, not hidden.
        trade = _make_trade(timestamp=NOW - timedelta(minutes=10))
        report = _make_enricher().enrich(trade)
        assert report.status == "REPORTABLE" and report.deadline_breached


class TestNotReportable:
    def test_out_of_scope_instrument_is_not_reportable(self):
        report = _make_enricher().enrich(_make_trade(symbol="EURUSD"))
        assert report.status == "NOT_REPORTABLE"
        assert report.status_reason == "FX spot out of scope"
        assert report.cfi_code is None

    def test_out_of_scope_wins_over_missing_participants(self):
        trade = _make_trade(symbol="EURUSD", buy_client_id="NOBODY")
        assert _make_enricher().enrich(trade).status == "NOT_REPORTABLE"

    def test_out_of_scope_without_reason_gets_generic_reason(self):
        data = _make_reference_data(
            instruments={"X": {"mifid_in_scope": False, "currency": "USD"}}
        )
        report = _make_enricher(data).enrich(_make_trade(symbol="X"))
        assert report.status_reason == "instrument out of scope"


class TestIncomplete:
    @pytest.mark.parametrize(
        "overrides, reason",
        [
            ({"symbol": "XYZ"}, "no reference data for instrument XYZ"),
            ({"buy_client_id": "VOL_B0001"}, "no LEI for buyer VOL_B0001"),
            ({"sell_client_id": "VOL_S0001"}, "no LEI for seller VOL_S0001"),
            ({"timestamp": None}, "trade has no execution timestamp"),
        ],
    )
    def test_missing_reference_data_is_flagged_not_defaulted(self, overrides, reason):
        report = _make_enricher().enrich(_make_trade(**overrides))
        assert report.status == "INCOMPLETE"
        assert report.status_reason == reason

    def test_all_problems_are_listed(self):
        trade = _make_trade(buy_client_id="X", sell_client_id="Y", timestamp=None)
        report = _make_enricher().enrich(trade)
        assert report.status_reason == (
            "no LEI for buyer X; no LEI for seller Y; trade has no execution timestamp"
        )
        assert report.publication_latency_ms is None
        assert report.deadline_breached is False

    def test_empty_reference_data_makes_everything_incomplete(self):
        report = ReportEnricher({}, clock=lambda: NOW).enrich(_make_trade())
        assert report.status == "INCOMPLETE"


class TestReplayAliases:
    def test_fix_replay_prefix_resolves_to_original_participant(self):
        trade = _make_trade(
            buy_client_id="RPL-ab12cd34-BUYER", sell_client_id="RPL-ab12cd34-SELLER"
        )
        report = _make_enricher().enrich(trade)
        assert report.status == "REPORTABLE"
        # The stored client ID stays as received, so replayed rows are traceable.
        assert report.buyer_client_id == "RPL-ab12cd34-BUYER"

    def test_alias_stripping_can_be_disabled(self):
        trade = _make_trade(buy_client_id="RPL-ab12cd34-BUYER")
        report = _make_enricher(alias_pattern="").enrich(trade)
        assert report.status == "INCOMPLETE"
