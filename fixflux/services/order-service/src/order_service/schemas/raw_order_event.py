# (from FIX gateway)

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class RawOrderEvent(BaseModel):

    symbol: str
    side: Literal["BUY", "SELL"]
    price: float
    quantity: int
    timestamp: datetime
    client_id: str = "UNKNOWN"
