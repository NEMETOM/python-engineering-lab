from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from compliance_service.rules.base import Rule, Severity, Violation


class VolumeSpikeRule(Rule):
    """Detects individual orders whose quantity far exceeds the baseline average for that symbol."""

    category = "surveillance"

    def __init__(self, config: dict):
        super().__init__(config)
        self._multiplier: float = config.get("spike_multiplier", 5.0)
        self._baseline_window = timedelta(
            seconds=config.get("baseline_window_seconds", 3600)
        )
        # symbol -> list of (timestamp, quantity)
        self._history: dict[str, list[tuple[datetime, int]]] = defaultdict(list)

    def check(self, event: dict[str, Any]) -> Violation | None:
        symbol = str(event.get("symbol") or event.get("55", ""))
        try:
            quantity = int(event.get("quantity") or event.get("38", 0))
        except (TypeError, ValueError):
            return None

        now = datetime.now(timezone.utc)
        cutoff = now - self._baseline_window
        history = self._history[symbol]
        history[:] = [(ts, q) for ts, q in history if ts > cutoff]

        violation = None
        if history:
            baseline_avg = sum(q for _, q in history) / len(history)
            if baseline_avg > 0 and quantity > baseline_avg * self._multiplier:
                actual_multiplier = quantity / baseline_avg
                violation = Violation(
                    rule_name=self.name,
                    rule_category=self.category,
                    severity=Severity.HIGH,
                    description=(
                        f"Volume spike on {symbol}: order qty {quantity:,} is "
                        f"{actual_multiplier:.1f}x the {self._baseline_window.seconds // 3600}h "
                        f"baseline average of {baseline_avg:,.0f}"
                    ),
                    raw_event=event,
                    client_id=event.get("client_id") or event.get("49"),
                    symbol=symbol,
                    metadata={
                        "quantity": quantity,
                        "baseline_avg": round(baseline_avg, 2),
                        "multiplier": round(actual_multiplier, 2),
                        "threshold_multiplier": self._multiplier,
                    },
                )

        history.append((now, quantity))
        return violation
