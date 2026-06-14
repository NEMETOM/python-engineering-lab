from unittest.mock import MagicMock

import pytest

from compliance_service.engine.risk_scorer import RiskScorer
from compliance_service.engine.rules_engine import RulesEngine
from compliance_service.rules.base import Severity, Violation


def _make_violation(severity: Severity = Severity.HIGH) -> Violation:
    return Violation(
        rule_name="TestRule",
        rule_category="compliance",
        severity=severity,
        description="test violation",
        raw_event={},
        client_id="C1",
    )


class TestRulesEngine:
    def test_returns_empty_list_when_no_violations(self):
        rule = MagicMock()
        rule.enabled = True
        rule.check.return_value = None
        engine = RulesEngine([rule])
        assert engine.evaluate({}) == []

    def test_collects_violations_from_all_rules(self):
        v1 = _make_violation(Severity.LOW)
        v2 = _make_violation(Severity.HIGH)
        r1, r2 = MagicMock(), MagicMock()
        r1.enabled, r2.enabled = True, True
        r1.check.return_value = v1
        r2.check.return_value = v2
        engine = RulesEngine([r1, r2])
        result = engine.evaluate({})
        assert result == [v1, v2]

    def test_skips_disabled_rules(self):
        rule = MagicMock()
        rule.enabled = False
        engine = RulesEngine([rule])
        engine.evaluate({})
        rule.check.assert_not_called()

    def test_continues_after_rule_exception(self):
        bad_rule = MagicMock()
        bad_rule.enabled = True
        bad_rule.name = "BadRule"
        bad_rule.check.side_effect = RuntimeError("boom")
        good_rule = MagicMock()
        good_rule.enabled = True
        good_rule.check.return_value = _make_violation()
        engine = RulesEngine([bad_rule, good_rule])
        result = engine.evaluate({})
        assert len(result) == 1


class TestRiskScorer:
    def setup_method(self):
        self.scorer = RiskScorer(
            {
                "weights": {"LOW": 1, "MEDIUM": 5, "HIGH": 20, "CRITICAL": 100},
                "high_risk_threshold": 200,
            }
        )

    @pytest.mark.parametrize(
        "severity, expected_score",
        [
            (Severity.LOW, 1.0),
            (Severity.MEDIUM, 5.0),
            (Severity.HIGH, 20.0),
            (Severity.CRITICAL, 100.0),
        ],
    )
    def test_score_matches_weight(self, severity, expected_score):
        violation = _make_violation(severity)
        assert self.scorer.score(violation) == expected_score

    def test_is_high_risk_above_threshold(self):
        assert self.scorer.is_high_risk(200.0) is True
        assert self.scorer.is_high_risk(199.9) is False
