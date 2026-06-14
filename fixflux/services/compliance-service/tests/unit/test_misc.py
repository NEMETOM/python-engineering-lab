"""Tests for config, schemas, loader, market_hours, and audit_logger."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from compliance_service.config import load_policies
from compliance_service.rules.compliance.market_hours import MarketHoursRule
from compliance_service.rules.loader import (
    build_compliance_rules,
    build_surveillance_rules,
)
from compliance_service.schemas.events import RawOrderEvent, ValidatedOrderEvent

# ── Config ────────────────────────────────────────────────────────────────────


class TestLoadPolicies:
    def test_loads_default_policy_file(self):
        policies = load_policies()
        assert "compliance" in policies
        assert "surveillance" in policies
        assert "risk_scoring" in policies

    def test_compliance_section_has_expected_rules(self):
        policies = load_policies()
        cfg = policies["compliance"]
        assert "market_hours" in cfg
        assert "trade_size" in cfg
        assert "allowed_symbols" in cfg

    def test_risk_scoring_weights_present(self):
        policies = load_policies()
        weights = policies["risk_scoring"]["weights"]
        assert set(weights.keys()) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def test_custom_path_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_policies(Path("/nonexistent/policies.yaml"))


# ── Schemas ───────────────────────────────────────────────────────────────────


class TestRawOrderEvent:
    def test_defaults_applied(self):
        event = RawOrderEvent()
        assert event.symbol == ""
        assert event.side == ""
        assert event.price == 0.0
        assert event.quantity == 0
        assert event.timestamp != ""

    def test_extra_fields_allowed(self):
        event = RawOrderEvent(symbol="EURUSD", custom_field="extra")
        assert event.symbol == "EURUSD"

    def test_to_dict_includes_all_fields(self):
        event = RawOrderEvent(
            symbol="EURUSD", client_id="C1", quantity=100, price=1.09, side="BUY"
        )
        d = event.to_dict()
        assert d["symbol"] == "EURUSD"
        assert d["client_id"] == "C1"


class TestValidatedOrderEvent:
    def test_required_fields(self):
        event = ValidatedOrderEvent(
            order_id="O1", symbol="BTCUSD", side="SELL", price=50000.0, quantity=1
        )
        assert event.order_id == "O1"
        assert event.symbol == "BTCUSD"

    def test_to_dict_returns_dict(self):
        event = ValidatedOrderEvent(
            order_id="O1", symbol="BTCUSD", side="SELL", price=50000.0, quantity=1
        )
        assert isinstance(event.to_dict(), dict)


# ── Loader ────────────────────────────────────────────────────────────────────


class TestRuleLoader:
    def setup_method(self):
        self.policies = load_policies()

    def test_builds_six_compliance_rules(self):
        rules = build_compliance_rules(self.policies)
        assert len(rules) == 6

    def test_builds_four_surveillance_rules(self):
        rules = build_surveillance_rules(self.policies)
        assert len(rules) == 4

    def test_compliance_rule_names(self):
        rules = build_compliance_rules(self.policies)
        names = {r.name for r in rules}
        assert "MissingClientIdRule" in names
        assert "TradeSizeRule" in names
        assert "InvalidSymbolRule" in names
        assert "DuplicateOrderRule" in names
        assert "PriceDeviationRule" in names
        assert "MarketHoursRule" in names

    def test_surveillance_rule_names(self):
        rules = build_surveillance_rules(self.policies)
        names = {r.name for r in rules}
        assert "WashTradingRule" in names
        assert "RapidFireRule" in names
        assert "VolumeSpikeRule" in names
        assert "RepeatedOrdersRule" in names

    def test_disabled_rule_is_not_enabled(self):
        policies = {
            "compliance": {"missing_client_id": {"enabled": False}},
            "surveillance": {},
        }
        rules = build_compliance_rules(policies)
        missing_id_rule = next(r for r in rules if r.name == "MissingClientIdRule")
        assert missing_id_rule.enabled is False

    def test_empty_config_uses_defaults(self):
        rules = build_compliance_rules({})
        assert len(rules) == 6
        for rule in rules:
            assert rule.enabled is True


# ── Market Hours ──────────────────────────────────────────────────────────────


class TestMarketHoursRule:
    def _rule(self, start="09:30", end="16:00", tz="UTC"):
        return MarketHoursRule(
            {"enabled": True, "start": start, "end": end, "timezone": tz}
        )

    def test_order_within_hours_passes(self):
        rule = self._rule()
        with patch(
            "compliance_service.rules.compliance.market_hours.datetime"
        ) as mock_dt:
            mock_now = MagicMock()
            mock_now.time.return_value = datetime(2026, 1, 1, 12, 0).time()
            mock_now.strftime.return_value = "12:00:00 UTC"
            mock_dt.now.return_value = mock_now
            assert rule.check({"client_id": "C1", "symbol": "EURUSD"}) is None

    def test_order_outside_hours_is_flagged(self):
        rule = self._rule()
        with patch(
            "compliance_service.rules.compliance.market_hours.datetime"
        ) as mock_dt:
            mock_now = MagicMock()
            mock_now.time.return_value = datetime(2026, 1, 1, 2, 0).time()
            mock_now.strftime.return_value = "02:00:00 UTC"
            mock_dt.now.return_value = mock_now
            violation = rule.check({"client_id": "C1", "symbol": "EURUSD"})
        assert violation is not None
        assert violation.severity.value == "MEDIUM"

    def test_disabled_rule_always_passes(self):
        rule = MarketHoursRule({"enabled": False})
        assert rule.check({"client_id": "C1", "symbol": "EURUSD"}) is None


# ── Audit Logger ──────────────────────────────────────────────────────────────


class TestAuditLogger:
    def test_logs_entry_with_checksum(self):
        from compliance_service.engine.audit_logger import AuditLogger

        mock_session = MagicMock()
        with patch(
            "compliance_service.engine.audit_logger.SessionLocal",
            return_value=mock_session,
        ):
            auditor = AuditLogger()
            auditor.log(
                event_type="order_received",
                action="raw_orders_consumed",
                payload={"symbol": "EURUSD", "quantity": 100},
                client_id="CLIENT1",
            )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.event_type == "order_received"
        assert added.client_id == "CLIENT1"
        assert added.checksum is not None
        assert len(added.checksum) == 64

    def test_checksum_is_deterministic(self):
        from compliance_service.engine.audit_logger import _checksum

        payload = {"symbol": "EURUSD", "price": 1.09, "quantity": 100}
        assert _checksum(payload) == _checksum(payload)

    def test_checksum_differs_for_different_payloads(self):
        from compliance_service.engine.audit_logger import _checksum

        assert _checksum({"a": 1}) != _checksum({"a": 2})

    def test_session_always_closed_on_db_error(self):
        from compliance_service.engine.audit_logger import AuditLogger

        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("DB down")
        with patch(
            "compliance_service.engine.audit_logger.SessionLocal",
            return_value=mock_session,
        ):
            auditor = AuditLogger()
            auditor.log(event_type="x", action="y", payload={})
        mock_session.close.assert_called_once()
