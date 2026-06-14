from datetime import datetime

from pydantic import BaseModel, Field


class TradeEvent(BaseModel):

    trade_id: str
    symbol: str
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
