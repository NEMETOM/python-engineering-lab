from shared.infrastructure.db import SessionLocal
from trade_store.models import TradeModel


class TradeRepository:

    def save(self, trade_event):

        session = SessionLocal()

        try:

            trade = TradeModel(
                trade_id=trade_event.trade_id,
                symbol=trade_event.symbol,
                buy_order_id=trade_event.buy_order_id,
                sell_order_id=trade_event.sell_order_id,
                price=trade_event.price,
                quantity=trade_event.quantity,
                timestamp=trade_event.timestamp,
            )

            session.add(trade)
            session.commit()

        finally:
            session.close()

    def get_all(self, symbol=None):

        session = SessionLocal()

        try:

            query = session.query(TradeModel)

            if symbol:

                query = query.filter(TradeModel.symbol == symbol)

            return [self._to_dict(t) for t in query.all()]

        finally:
            session.close()

    def get_by_id(self, trade_id):

        session = SessionLocal()

        try:

            trade = session.query(TradeModel).get(trade_id)

            return self._to_dict(trade) if trade else None

        finally:
            session.close()

    def _to_dict(self, trade):

        return {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "price": trade.price,
            "quantity": trade.quantity,
            "timestamp": trade.timestamp.isoformat(),
        }
