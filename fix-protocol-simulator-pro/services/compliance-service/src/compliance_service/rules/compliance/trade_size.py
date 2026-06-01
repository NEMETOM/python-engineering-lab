from typing import Any

from compliance_service.rules.base import Rule, Severity, Violation


class TradeSizeRule(Rule):
    """Flags orders whose quantity exceeds the per-symbol or default limit."""

    category = "compliance"

    def check(self, event: dict[str, Any]) -> Violation | None:
        symbol = event.get("symbol") or event.get("55", "")
        try:
            quantity = int(event.get("quantity") or event.get("38", 0))
        except (TypeError, ValueError):
            return None

        max_qty_cfg = self.config.get("max_quantity", {})
        limit = max_qty_cfg.get(symbol, max_qty_cfg.get("default", 10_000))

        if quantity > limit:
            client_id = event.get("client_id") or event.get("49")
            return Violation(
                rule_name=self.name,
                rule_category=self.category,
                severity=Severity.HIGH,
                description=(
                    f"Order quantity {quantity:,} exceeds the limit of {limit:,} "
                    f"for instrument {symbol}"
                ),
                raw_event=event,
                client_id=client_id,
                symbol=symbol,
                metadata={"quantity": quantity, "limit": limit},
            )
        return None
