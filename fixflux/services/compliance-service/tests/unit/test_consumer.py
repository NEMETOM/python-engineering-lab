from unittest.mock import MagicMock, patch

import pytest

import compliance_service.consumer  # noqa: F401  # ensure module is in sys.modules before @patch decorators fire


def _make_violation(rule_name="WashTradingRule", severity="HIGH", client_id="C001"):
    v = MagicMock()
    v.rule_name = rule_name
    v.severity.value = severity
    v.client_id = client_id
    return v


def _make_deps(violations=None):
    """Return (rules_engine, risk_scorer, repo, auditor) mocks."""
    rules_engine = MagicMock()
    rules_engine.evaluate.return_value = violations if violations is not None else []
    risk_scorer = MagicMock()
    risk_scorer.score.return_value = 10.0
    risk_scorer.is_high_risk.return_value = False
    repo = MagicMock()
    repo.save.return_value = "VID-001"
    repo.get_risk_score.return_value = None
    auditor = MagicMock()
    return rules_engine, risk_scorer, repo, auditor


class TestProcessEventMetrics:
    @patch("compliance_service.consumer.violations_detected")
    def test_compliant_event_does_not_increment_counter(self, mock_counter):
        from compliance_service.consumer import _process_event

        rules_engine, risk_scorer, repo, auditor = _make_deps(violations=[])
        _process_event({}, rules_engine, risk_scorer, repo, auditor, "raw_orders")
        mock_counter.labels.assert_not_called()

    @patch("compliance_service.consumer.violations_detected")
    def test_single_violation_increments_with_rule_and_severity(self, mock_counter):
        from compliance_service.consumer import _process_event

        violation = _make_violation(rule_name="WashTradingRule", severity="HIGH")
        rules_engine, risk_scorer, repo, auditor = _make_deps(violations=[violation])
        _process_event({}, rules_engine, risk_scorer, repo, auditor, "raw_orders")
        mock_counter.labels.assert_called_once_with(
            rule="WashTradingRule", severity="HIGH"
        )
        mock_counter.labels.return_value.inc.assert_called_once()

    @patch("compliance_service.consumer.violations_detected")
    def test_multiple_violations_each_increment_once(self, mock_counter):
        from compliance_service.consumer import _process_event

        violations = [
            _make_violation("WashTradingRule", "HIGH"),
            _make_violation("DuplicateOrderRule", "MEDIUM"),
        ]
        rules_engine, risk_scorer, repo, auditor = _make_deps(violations=violations)
        _process_event({}, rules_engine, risk_scorer, repo, auditor, "raw_orders")
        assert mock_counter.labels.call_count == 2
        mock_counter.labels.assert_any_call(rule="WashTradingRule", severity="HIGH")
        mock_counter.labels.assert_any_call(
            rule="DuplicateOrderRule", severity="MEDIUM"
        )

    @patch("compliance_service.consumer.violations_detected")
    def test_counter_not_incremented_when_rules_engine_raises(self, mock_counter):
        from compliance_service.consumer import _process_event

        rules_engine = MagicMock()
        rules_engine.evaluate.side_effect = Exception("rules engine failure")
        _, risk_scorer, repo, auditor = _make_deps()
        try:
            _process_event({}, rules_engine, risk_scorer, repo, auditor, "raw_orders")
        except Exception:  # noqa: BLE001, S110
            pass
        mock_counter.labels.assert_not_called()


class TestBuildRuleRegistry:
    def test_maps_catalog_ids_to_instances_in_order(self):
        from compliance_service.consumer import _build_rule_registry

        compliance_rules = [MagicMock() for _ in range(6)]
        surveillance_rules = [MagicMock() for _ in range(4)]
        registry = _build_rule_registry(compliance_rules, surveillance_rules)
        assert registry["missing_client_id"] is compliance_rules[0]
        assert registry["allowed_symbols"] is compliance_rules[5]
        assert registry["wash_trading"] is surveillance_rules[0]
        assert registry["repeated_orders"] is surveillance_rules[3]
        assert len(registry) == 10

    def test_raises_on_length_mismatch(self):
        from compliance_service.consumer import _build_rule_registry

        with pytest.raises(RuntimeError):
            _build_rule_registry([MagicMock()], [])


class TestRefreshRuleOverrides:
    @patch("compliance_service.consumer.time.sleep")
    @patch("compliance_service.consumer.RuleOverrideRepository")
    def test_applies_overrides_to_matching_registry_entries(
        self, mock_repo_cls, mock_sleep
    ):
        from compliance_service.consumer import _refresh_rule_overrides

        rule = MagicMock()
        rule.enabled = True
        registry = {"wash_trading": rule}
        mock_repo_cls.return_value.get_all.return_value = {"wash_trading": False}
        mock_sleep.side_effect = [None, RuntimeError("stop loop")]

        with pytest.raises(RuntimeError):
            _refresh_rule_overrides(registry)

        assert rule.enabled is False

    @patch("compliance_service.consumer.time.sleep")
    @patch("compliance_service.consumer.RuleOverrideRepository")
    def test_ignores_rule_ids_not_in_registry(self, mock_repo_cls, mock_sleep):
        from compliance_service.consumer import _refresh_rule_overrides

        mock_repo_cls.return_value.get_all.return_value = {"nonexistent_rule": True}
        mock_sleep.side_effect = [None, RuntimeError("stop loop")]

        with pytest.raises(RuntimeError):
            _refresh_rule_overrides({})

    @patch("compliance_service.consumer.time.sleep")
    @patch("compliance_service.consumer.RuleOverrideRepository")
    def test_loop_continues_after_repository_exception(self, mock_repo_cls, mock_sleep):
        from compliance_service.consumer import _refresh_rule_overrides

        mock_repo_cls.return_value.get_all.side_effect = [
            Exception("db unreachable"),
            {},
        ]
        mock_sleep.side_effect = [None, None, RuntimeError("stop loop")]

        with pytest.raises(RuntimeError):
            _refresh_rule_overrides({})

        assert mock_repo_cls.return_value.get_all.call_count == 2
