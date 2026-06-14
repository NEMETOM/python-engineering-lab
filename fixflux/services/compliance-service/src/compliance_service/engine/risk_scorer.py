from compliance_service.rules.base import Severity, Violation

_DEFAULT_WEIGHTS: dict[str, float] = {
    Severity.LOW.value: 1.0,
    Severity.MEDIUM.value: 5.0,
    Severity.HIGH.value: 20.0,
    Severity.CRITICAL.value: 100.0,
}


class RiskScorer:
    """Computes a numeric risk contribution for each violation and identifies high-risk clients."""

    def __init__(self, config: dict):
        raw_weights = config.get("weights", {})
        self._weights: dict[str, float] = {
            k: float(raw_weights.get(k, v)) for k, v in _DEFAULT_WEIGHTS.items()
        }
        self._high_risk_threshold: float = float(config.get("high_risk_threshold", 200))

    def score(self, violation: Violation) -> float:
        return self._weights.get(violation.severity.value, 1.0)

    def is_high_risk(self, total_score: float) -> bool:
        return total_score >= self._high_risk_threshold
