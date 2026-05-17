from dataclasses import dataclass


@dataclass
class Order:

    order_id: str
    side: str
    price: float
    quantity: int
    symbol: str = ""


@dataclass
class Trade:

    trade_id: str
    symbol: str
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: int
