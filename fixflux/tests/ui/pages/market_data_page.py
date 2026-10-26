from playwright.sync_api import Locator

from pages.console import ConsolePage


class QuoteRow:
    """One symbol's row; cells are tagged cell-<name> in market_data.html."""

    def __init__(self, row: Locator):
        self.row = row

    def _cell(self, name: str) -> Locator:
        return self.row.get_by_test_id(f"cell-{name}")

    @property
    def symbol(self) -> Locator:
        return self._cell("symbol")

    @property
    def bid(self) -> Locator:
        return self._cell("bid")

    @property
    def ask(self) -> Locator:
        return self._cell("ask")

    @property
    def mid(self) -> Locator:
        return self._cell("mid")

    @property
    def spread(self) -> Locator:
        return self._cell("spread")

    @property
    def last_trade(self) -> Locator:
        return self._cell("last")


class MarketDataPage(ConsolePage):
    """Market Data tab (templates/market_data.html)."""

    path = "/market-data"

    @property
    def connection_status(self) -> Locator:
        # "connecting" | "live" | "reconnecting - retry in Ns"
        return self.page.locator("#status")

    @property
    def waiting_message(self) -> Locator:
        return self.page.locator("#empty")

    @property
    def quotes_table(self) -> Locator:
        return self.page.locator("#quotes")

    @property
    def update_counter(self) -> Locator:
        return self.page.locator("#msg-count")

    def row(self, symbol: str) -> QuoteRow:
        return QuoteRow(
            self.page.locator(f'[data-testid="quote-row"][data-symbol="{symbol}"]')
        )
