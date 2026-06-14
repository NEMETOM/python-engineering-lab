from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from compliance_service.rules.base import Rule, Severity, Violation


class WashTradingRule(Rule):
    """Detects potential wash trading: same client trading both sides of the same instrument within a window."""

    category = "surveillance"

    def __init__(self, config: dict):
        super().__init__(config)
        self._window = timedelta(seconds=config.get("window_seconds", 300))
        # client_id -> list of (timestamp, symbol, side)
        self._history: dict[str, list[tuple[datetime, str, str]]] = defaultdict(list)

    def check(self, event: dict[str, Any]) -> Violation | None:
        client_id = str(event.get("client_id") or event.get("49", ""))
        symbol = str(event.get("symbol") or event.get("55", ""))
        raw_side = event.get("side") or event.get("54", "")
        side = (
            "BUY"
            if str(raw_side) == "1"
            else ("SELL" if str(raw_side) == "2" else str(raw_side))
        )
        now = datetime.now(timezone.utc)

        history = self._history[client_id]
        cutoff = now - self._window
        history[:] = [(ts, sym, s) for ts, sym, s in history if ts > cutoff]

        opposite = "SELL" if side == "BUY" else "BUY"
        for ts, sym, s in history:
            if sym == symbol and s == opposite:
                history.append((now, symbol, side))
                return Violation(
                    rule_name=self.name,
                    rule_category=self.category,
                    severity=Severity.CRITICAL,
                    description=(
                        f"Potential wash trading: {client_id} traded {symbol} "
                        f"{opposite} at {ts.strftime('%H:%M:%S')} "
                        f"and now {side} within {self._window.seconds}s"
                    ),
                    raw_event=event,
                    client_id=client_id,
                    symbol=symbol,
                    metadata={
                        "side": side,
                        "opposite_side": opposite,
                        "first_trade_at": ts.isoformat(),
                        "window_seconds": self._window.seconds,
                    },
                )

        history.append((now, symbol, side))
        return None
