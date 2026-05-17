import uuid
from datetime import datetime

from order_service.schemas import RawOrderEvent, ValidatedOrderEvent


class OrderTransformer:

    def transform(self, raw: RawOrderEvent) -> ValidatedOrderEvent:

        return ValidatedOrderEvent(
            order_id=str(uuid.uuid4()),
            symbol=raw.symbol,
            side=raw.side,
            price=raw.price,
            quantity=raw.quantity,
            timestamp=datetime.utcnow(),
        )
