from shared.infrastructure.db import Base
from sqlalchemy import Column, DateTime, Float, Integer, String


class TradeModel(Base):

    __tablename__ = "trades"

    trade_id = Column(String, primary_key=True)

    symbol = Column(String)

    buy_order_id = Column(String)

    sell_order_id = Column(String)

    price = Column(Float)

    quantity = Column(Integer)

    timestamp = Column(DateTime)
