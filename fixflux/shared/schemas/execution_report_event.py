import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ExecutionReportEvent(BaseModel):
    """
    FIX Execution Report (35=8) serialised for the Kafka execution_reports topic.

    Tag mapping:
        exec_id    -> Tag 17  (ExecID)         unique per report
        order_id   -> Tag 37  (OrderID)        exchange-assigned; also used as Tag 11
        cl_ord_id  -> Tag 11  (ClOrdID)        same as order_id (no client-assigned ref)
        client_id  -> Tag 49  (SenderCompID)   participant / firm identifier
        exec_type  -> Tag 150 (ExecType)       0=New, 8=Rejected, F=Trade/Fill
        ord_status -> Tag 39  (OrdStatus)      0=New, 2=Filled, 8=Rejected
        symbol     -> Tag 55  (Symbol)
        side       -> Tag 54  (Side)           BUY / SELL
        price      -> Tag 44  (Price)          original order limit price
        order_qty  -> Tag 38  (OrderQty)       original order quantity
        last_px    -> Tag 31  (LastPx)         fill price; set only for ExecType=F
        last_qty   -> Tag 32  (LastQty)        fill quantity; set only for ExecType=F
        leaves_qty -> Tag 151 (LeavesQty)      remaining open qty (0 for fills/rejects)
        cum_qty    -> Tag 14  (CumQty)         cumulative filled quantity
        reason     -> non-FIX                  rejection reason; null for approvals/fills
        timestamp  -> Tag 60  (TransactTime)   UTC time of this event
    """

    exec_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    cl_ord_id: str
    client_id: str
    exec_type: Literal["0", "8", "F"]
    ord_status: Literal["0", "2", "8"]
    symbol: str
    side: Literal["BUY", "SELL"]
    price: float
    order_qty: int
    last_px: Optional[float] = None
    last_qty: Optional[int] = None
    leaves_qty: int
    cum_qty: int
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
