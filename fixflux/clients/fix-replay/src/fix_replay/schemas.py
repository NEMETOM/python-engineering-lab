from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ReplayOrderEvent(BaseModel):
    """raw_orders payload; same shape as order_service.RawOrderEvent."""

    symbol: str
    side: Literal["BUY", "SELL"]
    price: float
    quantity: int
    timestamp: datetime
    client_id: str
