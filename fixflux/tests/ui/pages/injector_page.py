from playwright.sync_api import Locator

from pages.console import ConsolePage


class InjectorPage(ConsolePage):
    """Fix Msg Injector tab (templates/index.html)."""

    path = "/"

    @property
    def message_input(self) -> Locator:
        return self.page.locator("#raw_text")

    @property
    def inject_button(self) -> Locator:
        return self.page.locator("#submit")

    @property
    def result_summary(self) -> Locator:
        # e.g. "3/3 published, 0 rejected."
        return self.page.locator("#status")

    @property
    def published_results(self) -> Locator:
        return self.page.locator("#results").get_by_text("PUBLISHED", exact=True)

    def inject(self, fix_lines: list[str]) -> None:
        self.message_input.fill("\n".join(fix_lines))
        self.inject_button.click()
