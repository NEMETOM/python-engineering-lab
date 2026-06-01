from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from compliance_service.rules.base import Rule, Severity, Violation


class RepeatedOrdersRule(Rule):
    """Detects suspiciously identical orders from the same client within a rolling window."""

    category = "surveillance"

    def __init__(self, config: dict):
        super().__init__(config)
        self._threshold: int = config.get("repeat_threshold", 5)
        self._window = timedelta(seconds=config.get("window_seconds", 300))
        # (client_id, order_fingerprint) -> list of timestamps
        self._history: dict[tuple[str, str], list[datetime]] = defaultdict(list)

    def _fingerprint(self, event: dict[str, Any]) -> str:
        return "|".join(
            [
                str(event.get("symbol") or event.get("55", "")),
                str(event.get("side") or event.get("54", "")),
                str(event.get("price") or event.get("44", "")),
                str(event.get("quantity") or event.get("38", "")),
            ]
        )

    def check(self, event: dict[str, Any]) -> Violation | None:
        client_id = str(event.get("client_id") or event.get("49", ""))
        fp = self._fingerprint(event)
        key = (client_id, fp)
        now = datetime.now(timezone.utc)
        cutoff = now - self._window

        history = self._history[key]
        history[:] = [ts for ts in history if ts > cutoff]
        history.append(now)

        if len(history) >= self._threshold:
            return Violation(
                rule_name=self.name,
                rule_category=self.category,
                severity=Severity.MEDIUM,
                description=(
                    f"Suspicious repeated orders: {client_id} submitted an identical "
                    f"order {len(history)} times in {self._window.seconds}s "
                    f"(threshold {self._threshold})"
                ),
                raw_event=event,
                client_id=client_id,
                symbol=event.get("symbol") or event.get("55"),
                metadata={
                    "repeat_count": len(history),
                    "threshold": self._threshold,
                    "window_seconds": self._window.seconds,
                    "fingerprint": fp,
                },
            )
        return None
