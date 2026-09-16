from datetime import UTC, datetime


class MarketCache:
    """Tracks (best_bid, best_ask, last_trade_price) per symbol.

    Keyed by symbol rather than one global state, since order_book_updates
    and trades cover several instruments (EURUSD, BTCUSD, AAPL, ...) and
    mixing them into one shared price would make each symbol's snapshot
    wrong the moment any other symbol updates.
    """

    def __init__(self):
        self._state: dict[str, dict] = {}

    def _entry(self, symbol: str) -> dict:
        return self._state.setdefault(
            symbol,
            {"best_bid": None, "best_ask": None, "last_trade_price": None},
        )

    def update_trade(self, trade: dict) -> None:
        symbol = trade.get("symbol")
        if not symbol:
            return
        self._entry(symbol)["last_trade_price"] = trade["price"]

    def update_order_book(self, book: dict) -> None:
        symbol = book.get("symbol")
        if not symbol:
            return
        entry = self._entry(symbol)
        entry["best_bid"] = book["best_bid"]
        entry["best_ask"] = book["best_ask"]

    def snapshot(self) -> dict[str, dict]:
        now = datetime.now(tz=UTC).isoformat()
        result = {}
        for symbol, entry in self._state.items():
            mid = None
            if entry["best_bid"] and entry["best_ask"]:
                mid = (entry["best_bid"] + entry["best_ask"]) / 2
            result[symbol] = {
                "symbol": symbol,
                "best_bid": entry["best_bid"],
                "best_ask": entry["best_ask"],
                "mid_price": mid,
                "last_trade_price": entry["last_trade_price"],
                "timestamp": now,
            }
        return result
