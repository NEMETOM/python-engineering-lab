from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from compliance_service.rules.base import Rule, Severity, Violation


class RapidFireRule(Rule):
    """Detects clients submitting an unusually high number of orders in a short window."""

    category = "surveillance"

    def __init__(self, config: dict):
        super().__init__(config)
        self._max_orders: int = config.get("max_orders", 10)
        self._window = timedelta(seconds=config.get("window_seconds", 60))
        self._history: dict[str, list[datetime]] = defaultdict(list)

    def check(self, event: dict[str, Any]) -> Violation | None:
        client_id = str(event.get("client_id") or event.get("49", ""))
        now = datetime.now(timezone.utc)
        cutoff = now - self._window

        history = self._history[client_id]
        history[:] = [ts for ts in history if ts > cutoff]
        history.append(now)

        if len(history) > self._max_orders:
            return Violation(
                rule_name=self.name,
                rule_category=self.category,
                severity=Severity.HIGH,
                description=(
                    f"Rapid-fire orders: {client_id} submitted {len(history)} orders "
                    f"in {self._window.seconds}s (limit {self._max_orders})"
                ),
                raw_event=event,
                client_id=client_id,
                symbol=event.get("symbol") or event.get("55"),
                metadata={
                    "order_count": len(history),
                    "window_seconds": self._window.seconds,
                    "limit": self._max_orders,
                },
            )
        return None
