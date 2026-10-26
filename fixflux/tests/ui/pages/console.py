from playwright.sync_api import Locator, Page


class ConsoleNav:
    """The tab bar shared by every Console page (templates/_shell.html)."""

    def __init__(self, page: Page):
        self._nav = page.get_by_role("navigation")

    def tab(self, name: str) -> Locator:
        return self._nav.get_by_role("link", name=name)

    @property
    def current_tabs(self) -> Locator:
        # The active tab carries aria-current="page"; exactly one should.
        return self._nav.locator('[aria-current="page"]')

    def open_tab(self, name: str) -> None:
        self.tab(name).click()


class ConsolePage:
    """Base for one Console tab. Pages expose locators and actions only;
    assertions stay in the step definitions."""

    path = "/"

    def __init__(self, page: Page):
        self.page = page
        self.nav = ConsoleNav(page)

    def open(self) -> "ConsolePage":
        self.page.goto(self.path)
        return self

    def reload(self) -> None:
        self.page.reload()

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role("heading", level=1)
