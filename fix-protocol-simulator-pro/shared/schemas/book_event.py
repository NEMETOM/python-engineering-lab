from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class BookEvent(BaseModel):

    symbol: str
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    mid_price: Optional[float] = None
    last_trade_price: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
