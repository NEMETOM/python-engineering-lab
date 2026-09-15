from datetime import datetime

from pydantic import BaseModel


class MarketDataEvent(BaseModel):
    """Shape of a message on the market_data Kafka topic - one per symbol,
    published only when (best_bid, best_ask, last_trade_price) changes."""

    symbol: str

    best_bid: float | None

    best_ask: float | None

    mid_price: float | None

    last_trade_price: float | None

    timestamp: datetime
