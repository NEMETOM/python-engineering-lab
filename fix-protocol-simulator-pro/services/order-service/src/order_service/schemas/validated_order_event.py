# (to matching engine)

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ValidatedOrderEvent(BaseModel):

    order_id: str

    symbol: str

    side: Literal["BUY", "SELL"]

    price: float = Field(..., gt=0)

    quantity: int = Field(..., gt=0)

    timestamp: datetime
