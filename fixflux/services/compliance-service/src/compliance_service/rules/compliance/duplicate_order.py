from datetime import datetime, timezone
from typing import Any

from compliance_service.rules.base import Rule, Severity, Violation


class DuplicateOrderRule(Rule):
    """Flags identical orders from the same client within a rolling time window."""

    category = "compliance"

    def __init__(self, config: dict):
        super().__init__(config)
        self._window: int = config.get("window_seconds", 60)
        self._seen: dict[str, datetime] = {}

    def _order_key(self, event: dict[str, Any]) -> str:
        return "|".join(
            [
                str(event.get("client_id") or event.get("49", "")),
                str(event.get("symbol") or event.get("55", "")),
                str(event.get("side") or event.get("54", "")),
                str(event.get("price") or event.get("44", "")),
                str(event.get("quantity") or event.get("38", "")),
            ]
        )

    def check(self, event: dict[str, Any]) -> Violation | None:
        key = self._order_key(event)
        now = datetime.now(timezone.utc)

        self._seen = {
            k: v
            for k, v in self._seen.items()
            if (now - v).total_seconds() < self._window
        }

        if key in self._seen:
            client_id = event.get("client_id") or event.get("49")
            age = (now - self._seen[key]).total_seconds()
            return Violation(
                rule_name=self.name,
                rule_category=self.category,
                severity=Severity.MEDIUM,
                description=(
                    f"Duplicate order detected for {client_id}: "
                    f"identical order submitted {age:.1f}s ago (window {self._window}s)"
                ),
                raw_event=event,
                client_id=client_id,
                symbol=event.get("symbol") or event.get("55"),
                metadata={"window_seconds": self._window, "age_seconds": age},
            )

        self._seen[key] = now
        return None
