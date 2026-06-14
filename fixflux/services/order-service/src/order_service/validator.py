from order_service.schemas import RawOrderEvent
from shared.exceptions import ValidationError


class OrderValidator:

    def validate(self, event: RawOrderEvent):

        if event.price <= 0:
            raise ValidationError("price must be positive")

        if event.quantity <= 0:
            raise ValidationError("quantity must be positive")

        if event.side not in ["BUY", "SELL"]:
            raise ValidationError("invalid side")

        return True
