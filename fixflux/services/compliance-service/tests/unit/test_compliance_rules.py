import pytest

from compliance_service.rules.compliance.duplicate_order import DuplicateOrderRule
from compliance_service.rules.compliance.invalid_symbol import InvalidSymbolRule
from compliance_service.rules.compliance.missing_client_id import MissingClientIdRule
from compliance_service.rules.compliance.price_deviation import PriceDeviationRule
from compliance_service.rules.compliance.trade_size import TradeSizeRule


class TestMissingClientIdRule:
    def setup_method(self):
        self.rule = MissingClientIdRule({"enabled": True})

    def test_flags_when_both_fields_absent(self):
        violation = self.rule.check({"symbol": "EURUSD", "quantity": 100})
        assert violation is not None
        assert violation.severity.value == "HIGH"
        assert "client" in violation.description.lower()

    def test_passes_with_client_id_field(self):
        assert self.rule.check({"client_id": "CLIENT1", "symbol": "EURUSD"}) is None

    def test_passes_with_fix_tag_49(self):
        assert self.rule.check({"49": "CLIENT1", "55": "EURUSD"}) is None

    def test_rule_name_matches_class(self):
        assert self.rule.name == "MissingClientIdRule"


class TestTradeSizeRule:
    @pytest.mark.parametrize(
        "symbol, quantity, limit_cfg, should_flag",
        [
            ("EURUSD", 500, {"default": 10000}, False),
            ("EURUSD", 15000, {"default": 10000}, True),
            ("BTCUSD", 50, {"default": 10000, "BTCUSD": 100}, False),
            ("BTCUSD", 200, {"default": 10000, "BTCUSD": 100}, True),
        ],
    )
    def test_size_limit(self, symbol, quantity, limit_cfg, should_flag):
        rule = TradeSizeRule({"enabled": True, "max_quantity": limit_cfg})
        event = {"client_id": "C1", "symbol": symbol, "quantity": quantity}
        result = rule.check(event)
        assert (result is not None) == should_flag

    def test_violation_severity_is_high(self):
        rule = TradeSizeRule({"enabled": True, "max_quantity": {"default": 100}})
        violation = rule.check({"client_id": "C1", "symbol": "AAPL", "quantity": 9999})
        assert violation is not None
        assert violation.severity.value == "HIGH"
        assert violation.metadata["quantity"] == 9999
        assert violation.metadata["limit"] == 100


class TestInvalidSymbolRule:
    def setup_method(self):
        self.rule = InvalidSymbolRule(
            {"enabled": True, "symbols": ["EURUSD", "BTCUSD"]}
        )

    def test_flags_unknown_symbol(self):
        violation = self.rule.check({"client_id": "C1", "symbol": "XYZABC"})
        assert violation is not None
        assert violation.severity.value == "CRITICAL"

    def test_passes_approved_symbol(self):
        assert self.rule.check({"client_id": "C1", "symbol": "EURUSD"}) is None

    def test_no_symbols_configured_passes_all(self):
        rule = InvalidSymbolRule({"enabled": True, "symbols": []})
        assert rule.check({"symbol": "ANYTHING"}) is None


class TestDuplicateOrderRule:
    def test_second_identical_order_is_flagged(self):
        rule = DuplicateOrderRule({"enabled": True, "window_seconds": 60})
        event = {
            "client_id": "C1",
            "symbol": "EURUSD",
            "side": "BUY",
            "price": "1.09",
            "quantity": "100",
        }
        assert rule.check(event) is None
        violation = rule.check(event)
        assert violation is not None
        assert "Duplicate" in violation.description

    def test_different_prices_not_flagged(self):
        rule = DuplicateOrderRule({"enabled": True, "window_seconds": 60})
        e1 = {
            "client_id": "C1",
            "symbol": "EURUSD",
            "side": "BUY",
            "price": "1.09",
            "quantity": "100",
        }
        e2 = {**e1, "price": "1.10"}
        assert rule.check(e1) is None
        assert rule.check(e2) is None


class TestPriceDeviationRule:
    def test_first_event_always_passes(self):
        rule = PriceDeviationRule({"enabled": True, "max_deviation_pct": 5.0})
        assert (
            rule.check({"client_id": "C1", "symbol": "EURUSD", "price": 1.09}) is None
        )

    def test_within_threshold_passes(self):
        rule = PriceDeviationRule({"enabled": True, "max_deviation_pct": 5.0})
        rule.check({"client_id": "C1", "symbol": "EURUSD", "price": 1.09})
        assert (
            rule.check({"client_id": "C1", "symbol": "EURUSD", "price": 1.10}) is None
        )

    def test_large_deviation_is_flagged(self):
        rule = PriceDeviationRule({"enabled": True, "max_deviation_pct": 5.0})
        rule.check({"client_id": "C1", "symbol": "EURUSD", "price": 1.09})
        violation = rule.check({"client_id": "C1", "symbol": "EURUSD", "price": 2.50})
        assert violation is not None
        assert violation.metadata["deviation_pct"] > 5.0
