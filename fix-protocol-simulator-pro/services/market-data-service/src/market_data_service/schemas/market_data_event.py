from datetime import datetime

from pydantic import BaseModel


class MarketDataEvent(BaseModel):

    symbol: str

    best_bid: float | None

    best_ask: float | None

    mid_price: float | None

    last_trade_price: float | None

    timestamp: datetime
