from typing import Any

from compliance_service.rules.base import Rule, Severity, Violation


class MissingClientIdRule(Rule):
    """Flags any order that arrives without a client identifier."""

    category = "compliance"

    def check(self, event: dict[str, Any]) -> Violation | None:
        client_id = event.get("client_id") or event.get("49")
        if not client_id:
            return Violation(
                rule_name=self.name,
                rule_category=self.category,
                severity=Severity.HIGH,
                description="Order received with missing client identifier (client_id / SenderCompID tag 49)",
                raw_event=event,
                symbol=event.get("symbol") or event.get("55"),
            )
        return None
