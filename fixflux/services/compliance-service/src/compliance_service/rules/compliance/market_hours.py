from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from compliance_service.rules.base import Rule, Severity, Violation


class MarketHoursRule(Rule):
    """Flags orders submitted outside configured market hours."""

    category = "compliance"

    def check(self, event: dict[str, Any]) -> Violation | None:
        if not self.enabled:
            return None

        start_str = self.config.get("start", "09:30")
        end_str = self.config.get("end", "16:00")
        tz_name = self.config.get("timezone", "UTC")

        now = datetime.now(ZoneInfo(tz_name))
        market_open = time.fromisoformat(start_str)
        market_close = time.fromisoformat(end_str)

        if not (market_open <= now.time() <= market_close):
            client_id = event.get("client_id") or event.get("49")
            return Violation(
                rule_name=self.name,
                rule_category=self.category,
                severity=Severity.MEDIUM,
                description=(
                    f"Order submitted outside market hours "
                    f"({start_str}-{end_str} {tz_name}); "
                    f"current time {now.strftime('%H:%M:%S %Z')}"
                ),
                raw_event=event,
                client_id=client_id,
                symbol=event.get("symbol") or event.get("55"),
                metadata={
                    "current_time": now.isoformat(),
                    "window": f"{start_str}-{end_str}",
                },
            )
        return None
