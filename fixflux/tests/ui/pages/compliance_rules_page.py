from playwright.sync_api import Locator

from pages.console import ConsolePage


class RuleCard:
    """One rule's card: its Active/Disabled badge and on/off switch."""

    def __init__(self, card: Locator):
        self.card = card

    @property
    def badge(self) -> Locator:
        return self.card.get_by_test_id("rule-badge")

    @property
    def switch(self) -> Locator:
        # role="switch" with aria-checked="true" | "false"
        return self.card.get_by_role("switch")

    def toggle(self) -> None:
        self.switch.click()


class ComplianceRulesPage(ConsolePage):
    """Compliance Rules tab (templates/admin_compliance.html)."""

    path = "/admin/compliance"

    def rule(self, rule_id: str) -> RuleCard:
        return RuleCard(
            self.page.locator(f'[data-testid="rule-card"][data-rule-id="{rule_id}"]')
        )
