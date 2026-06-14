from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ValidatedOrder(BaseModel):
    order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    price: float
    quantity: int
    timestamp: datetime
    client_id: str = "UNKNOWN"


class TradeEvent(BaseModel):
    trade_id: str
    symbol: str
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: int


class RiskDecision(BaseModel):
    approved: bool
    reason: Optional[str] = None


class RejectedOrderEvent(BaseModel):
    order_id: str
    client_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    price: float
    quantity: int
    reason: str
    timestamp: datetime
