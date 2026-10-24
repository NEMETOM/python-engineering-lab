import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fix_replay.config import INPUT_TOPIC
from fix_replay.parser import ReplayOrder
from fix_replay.schemas import ReplayOrderEvent


class Replayer:
    def __init__(
        self,
        producer: Any,
        client_prefix: str,
        rate: float,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.producer = producer
        self.client_prefix = client_prefix
        self.interval = 1.0 / rate if rate > 0 else 0.0
        self.sleep = sleep

    def to_event(self, order: ReplayOrder) -> dict:
        # Namespacing the client keeps every client's orders together (risk
        # limits, wash-trading detection still see one participant) while
        # isolating the run from earlier runs' open orders and positions.
        return ReplayOrderEvent(
            symbol=order.symbol,
            side=order.side,  # type: ignore[arg-type]
            price=order.price,
            quantity=order.quantity,
            timestamp=datetime.now(UTC),
            client_id=f"{self.client_prefix}{order.client_id}",
        ).model_dump(mode="json")

    def send(self, orders: list[ReplayOrder]) -> int:
        for i, order in enumerate(orders):
            if i and self.interval:
                self.sleep(self.interval)
            self.producer.send(INPUT_TOPIC, self.to_event(order))
        self.producer.flush()
        return len(orders)
