from collections import defaultdict


class PositionStore:
    """
    Tracks per-client, per-symbol net positions from filled trades
    and open order counts from risk-approved pending orders.

    net_qty > 0 = long, net_qty < 0 = short
    """

    def __init__(self):
        # (client_id, symbol) -> net filled qty
        self._net: dict[tuple, int] = defaultdict(int)
        # order_id -> {client_id, symbol, side, quantity}
        self._open: dict[str, dict] = {}

    def record_open_order(
        self, order_id: str, client_id: str, symbol: str, side: str, quantity: int
    ) -> None:
        self._open[order_id] = {
            "client_id": client_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }

    def fill_order(self, order_id: str, quantity: int | None = None) -> None:
        """Apply a fill of `quantity` (default: everything still open).

        A partly filled order stays open with its remaining quantity - the
        matching engine keeps that remainder resting in the book, so it must
        still count towards the open-order limit, and only the filled part
        may move the position.
        """
        meta = self._open.get(order_id)
        if meta is None:
            return
        filled = (
            meta["quantity"] if quantity is None else min(quantity, meta["quantity"])
        )
        meta["quantity"] -= filled
        if meta["quantity"] <= 0:
            del self._open[order_id]
        delta = filled if meta["side"] == "BUY" else -filled
        self._net[(meta["client_id"], meta["symbol"])] += delta

    def get_net_position(self, client_id: str, symbol: str) -> int:
        return self._net[(client_id, symbol)]

    def get_gross_position(self, client_id: str, symbol: str) -> int:
        return abs(self._net[(client_id, symbol)])

    def get_open_order_count(self, client_id: str) -> int:
        return sum(1 for m in self._open.values() if m["client_id"] == client_id)
