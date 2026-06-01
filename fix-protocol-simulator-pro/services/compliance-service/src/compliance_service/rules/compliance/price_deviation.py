from collections import defaultdict
from typing import Any

from compliance_service.rules.base import Rule, Severity, Violation

_ROLLING_WINDOW = 10


class PriceDeviationRule(Rule):
    """Flags orders whose price deviates more than a threshold from the rolling average."""

    category = "compliance"

    def __init__(self, config: dict):
        super().__init__(config)
        self._max_deviation_pct: float = config.get("max_deviation_pct", 5.0)
        self._history: dict[str, list[float]] = defaultdict(list)

    def check(self, event: dict[str, Any]) -> Violation | None:
        symbol = event.get("symbol") or event.get("55", "")
        try:
            price = float(event.get("price") or event.get("44", 0))
        except (TypeError, ValueError):
            return None

        if not price:
            return None

        history = self._history[symbol]

        if history:
            reference = sum(history) / len(history)
            deviation_pct = abs(price - reference) / reference * 100
            if deviation_pct > self._max_deviation_pct:
                client_id = event.get("client_id") or event.get("49")
                history.append(price)
                if len(history) > _ROLLING_WINDOW:
                    history.pop(0)
                return Violation(
                    rule_name=self.name,
                    rule_category=self.category,
                    severity=Severity.HIGH,
                    description=(
                        f"Price {price} for {symbol} deviates {deviation_pct:.1f}% "
                        f"from rolling average {reference:.4f} "
                        f"(threshold {self._max_deviation_pct}%)"
                    ),
                    raw_event=event,
                    client_id=client_id,
                    symbol=symbol,
                    metadata={
                        "price": price,
                        "reference": reference,
                        "deviation_pct": round(deviation_pct, 2),
                        "threshold_pct": self._max_deviation_pct,
                    },
                )

        history.append(price)
        if len(history) > _ROLLING_WINDOW:
            history.pop(0)
        return None
