from datetime import datetime

from pydantic import BaseModel


class OrderBookEvent(BaseModel):

    symbol: str

    best_bid: float

    best_ask: float

    timestamp: datetime
