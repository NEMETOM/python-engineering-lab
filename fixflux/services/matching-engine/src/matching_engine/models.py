from dataclasses import dataclass


@dataclass
class Order:
    order_id: str
    side: str
    price: float
    quantity: int
    symbol: str = ""
    client_id: str = "UNKNOWN"
    order_qty: int = 0  # original quantity before matching; used in leaves_qty/cum_qty


@dataclass
class Trade:
    trade_id: str
    symbol: str
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: int
    buy_client_id: str = "UNKNOWN"
    sell_client_id: str = "UNKNOWN"
    buy_order_qty: int = 0
    sell_order_qty: int = 0
