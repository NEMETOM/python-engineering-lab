from unittest.mock import MagicMock, patch

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
        except Exception:
            pass
        mock_counter.labels.assert_not_called()
