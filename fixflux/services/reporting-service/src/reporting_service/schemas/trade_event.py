from datetime import datetime

from pydantic import BaseModel, Field


class TradeEvent(BaseModel):
    """Inbound `trades` payload from matching-engine."""

    trade_id: str
    symbol: str
    buy_order_id: str
    sell_order_id: str
    price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    buy_client_id: str = "UNKNOWN"
    sell_client_id: str = "UNKNOWN"
    # Execution time. Absent from trades produced before matching-engine
    # started sending it; such trades are reported INCOMPLETE.
    timestamp: datetime | None = None
