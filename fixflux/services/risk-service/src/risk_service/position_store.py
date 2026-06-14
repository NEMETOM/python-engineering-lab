from collections import defaultdict
from typing import Dict


class PositionStore:
    """
    Tracks per-client, per-symbol net positions from filled trades
    and open order counts from risk-approved pending orders.

    net_qty > 0 = long, net_qty < 0 = short
    """

    def __init__(self):
        # (client_id, symbol) -> net filled qty
        self._net: Dict[tuple, int] = defaultdict(int)
        # order_id -> {client_id, symbol, side, quantity}
        self._open: Dict[str, dict] = {}

    def record_open_order(
        self, order_id: str, client_id: str, symbol: str, side: str, quantity: int
    ) -> None:
        self._open[order_id] = {
            "client_id": client_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }

    def fill_order(self, order_id: str) -> None:
        meta = self._open.pop(order_id, None)
        if meta is None:
            return
        delta = meta["quantity"] if meta["side"] == "BUY" else -meta["quantity"]
        self._net[(meta["client_id"], meta["symbol"])] += delta

    def get_net_position(self, client_id: str, symbol: str) -> int:
        return self._net[(client_id, symbol)]

    def get_gross_position(self, client_id: str, symbol: str) -> int:
        return abs(self._net[(client_id, symbol)])

    def get_open_order_count(self, client_id: str) -> int:
        return sum(1 for m in self._open.values() if m["client_id"] == client_id)
