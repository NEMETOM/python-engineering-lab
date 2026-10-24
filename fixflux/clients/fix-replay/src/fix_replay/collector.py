import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from shared.schemas import ExecutionReportEvent

_ACK_EXEC_TYPES = {"0", "8"}  # New, Rejected - exactly one per order


@dataclass
class CollectResult:
    reports: list[ExecutionReportEvent] = field(default_factory=list)
    acks: int = 0
    timed_out: bool = False


def collect(
    consumer: Any,
    client_prefix: str,
    expected_acks: int,
    timeout_s: float,
    settle_s: float,
    clock: Callable[[], float] = time.monotonic,
) -> CollectResult:
    """Read this run's execution reports until every order is acked and no
    further report has arrived for settle_s (fills trail their New ack), or
    until timeout_s elapses."""
    result = CollectResult()
    start = clock()
    last_seen = start

    while True:
        now = clock()
        if result.acks >= expected_acks and now - last_seen >= settle_s:
            return result
        if now - start >= timeout_s:
            result.timed_out = result.acks < expected_acks
            return result

        batch = consumer.poll(timeout_ms=200)
        for records in batch.values():
            for record in records:
                value = record.value
                if not str(value.get("client_id", "")).startswith(client_prefix):
                    continue
                report = ExecutionReportEvent(**value)
                result.reports.append(report)
                if report.exec_type in _ACK_EXEC_TYPES:
                    result.acks += 1
                last_seen = clock()
