from typing import Any

from compliance_service.rules.base import Rule, Severity, Violation


class InvalidSymbolRule(Rule):
    """Flags orders for instruments not on the approved symbol list."""

    category = "compliance"

    def __init__(self, config: dict):
        super().__init__(config)
        self._allowed: set[str] = set(config.get("symbols", []))

    def check(self, event: dict[str, Any]) -> Violation | None:
        if not self._allowed:
            return None

        symbol = event.get("symbol") or event.get("55", "")
        if symbol not in self._allowed:
            client_id = event.get("client_id") or event.get("49")
            return Violation(
                rule_name=self.name,
                rule_category=self.category,
                severity=Severity.CRITICAL,
                description=(
                    f"Order for unknown or unapproved instrument '{symbol}'. "
                    f"Approved symbols: {sorted(self._allowed)}"
                ),
                raw_event=event,
                client_id=client_id,
                symbol=symbol,
                metadata={"symbol": symbol, "allowed": sorted(self._allowed)},
            )
        return None
