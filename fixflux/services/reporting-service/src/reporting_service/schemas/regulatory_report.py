from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, model_validator

from reporting_service.lei import is_valid_lei


def _check_lei(value: str) -> str:
    if not is_valid_lei(value):
        raise ValueError(f"not a valid ISO 17442 LEI: {value!r}")
    return value


Lei = Annotated[str, AfterValidator(_check_lei)]
CfiCode = Annotated[str, Field(pattern=r"^[A-Z]{6}$")]  # ISO 10962, 6 characters
TradingCapacity = Literal["DEAL", "MTCH", "AOTC"]  # RTS 22 field 29
ReportStatus = Literal["REPORTABLE", "NOT_REPORTABLE", "INCOMPLETE"]


class RegulatoryTradeReport(BaseModel):
    """One regulatory record per trade.

    Two regimes, kept apart deliberately:
    - Public post-trade transparency (RTS 1/2 Annex I Table 3): instrument,
      price, currency, quantity, trading and publication time. Never includes
      counterparty identity - the transaction ID "shall not disclose the
      identity of the counterparties".
    - Restricted, transaction-reporting-style fields (RTS 22): buyer/seller
      LEI, trading capacity, CFI code. Stored for the regulator, never for
      publication.
    """

    # Public transparency fields
    trade_id: str
    symbol: str
    price: float
    price_currency: str | None
    quantity: int
    trading_timestamp: datetime | None
    reporting_timestamp: datetime

    # Restricted fields
    buyer_client_id: str
    seller_client_id: str
    buyer_lei: Lei | None
    seller_lei: Lei | None
    buyer_trading_capacity: TradingCapacity | None
    seller_trading_capacity: TradingCapacity | None
    cfi_code: CfiCode | None
    asset_class: str | None

    # Outcome
    status: ReportStatus
    status_reason: str | None
    publication_latency_ms: int | None
    deadline_breached: bool

    @model_validator(mode="after")
    def _reportable_is_complete(self) -> "RegulatoryTradeReport":
        if self.status != "REPORTABLE":
            return self
        required = (
            "trading_timestamp",
            "price_currency",
            "buyer_lei",
            "seller_lei",
            "buyer_trading_capacity",
            "seller_trading_capacity",
            "cfi_code",
        )
        missing = [name for name in required if getattr(self, name) is None]
        if missing:
            raise ValueError(f"REPORTABLE report missing {', '.join(missing)}")
        return self
