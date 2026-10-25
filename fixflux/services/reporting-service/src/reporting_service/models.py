from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
)

from shared.infrastructure.db import Base

UNIQUE_TRADE_CONSTRAINT = "uq_regulatory_reports_trade_id"


class RegulatoryReportModel(Base):

    __tablename__ = "regulatory_reports"
    # One report per trade: Kafka redelivery (at-least-once consumption) must
    # not produce a second regulatory record for the same trade.
    __table_args__ = (UniqueConstraint("trade_id", name=UNIQUE_TRADE_CONSTRAINT),)

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Public post-trade transparency fields (RTS 1/2 Annex I Table 3)
    trade_id = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    price_currency = Column(String)
    quantity = Column(Integer, nullable=False)
    trading_timestamp = Column(DateTime(timezone=True))
    reporting_timestamp = Column(DateTime(timezone=True), nullable=False)

    # Restricted fields - never part of a public publication
    buyer_client_id = Column(String, nullable=False)
    seller_client_id = Column(String, nullable=False)
    buyer_lei = Column(String(20))
    seller_lei = Column(String(20))
    buyer_trading_capacity = Column(String(4))
    seller_trading_capacity = Column(String(4))
    cfi_code = Column(String(6))
    asset_class = Column(String)

    status = Column(String, nullable=False)
    status_reason = Column(String)
    publication_latency_ms = Column(Integer)
    deadline_breached = Column(Boolean, nullable=False)
