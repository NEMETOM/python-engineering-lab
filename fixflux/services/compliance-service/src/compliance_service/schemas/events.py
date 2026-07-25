from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class RawOrderEvent(BaseModel):
    """Represents a message from the raw_orders Kafka topic."""

    symbol: str = ""
    side: str = ""
    price: float = 0.0
    quantity: int = 0
    client_id: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    # Allow extra fields so FIX tag=value pairs passed as dicts are accepted
    model_config = {"extra": "allow"}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class ValidatedOrderEvent(BaseModel):
    """Represents a message from the validated_orders Kafka topic."""

    order_id: str
    symbol: str
    side: str
    price: float
    quantity: int
    client_id: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    model_config = {"extra": "allow"}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
