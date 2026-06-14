from datetime import datetime

from pydantic import BaseModel


class TradeEvent(BaseModel):

    symbol: str

    price: float

    quantity: int

    timestamp: datetime
