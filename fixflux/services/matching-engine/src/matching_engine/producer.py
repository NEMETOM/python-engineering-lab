from datetime import UTC, datetime

from opentelemetry import trace

from matching_engine.infrastructure.kafka_client import (
    create_exec_report_producer,
    create_producer,
)
from matching_engine.models import Trade
from matching_engine.utils.logger import get_logger
from shared.observability.metrics import (
    exec_reports_emitted,
    new_to_fill_latency_seconds,
)
from shared.observability.tracing import inject_ctx
from shared.schemas.execution_report_event import ExecutionReportEvent

logger = get_logger(__name__)

_EXEC_REPORTS_TOPIC = "execution_reports"
_tracer = trace.get_tracer("matching-engine")


def _new_to_fill_latency_seconds(approved_at: str) -> float | None:
    if not approved_at:
        return None
    try:
        return (datetime.now(UTC) - datetime.fromisoformat(approved_at)).total_seconds()
    except ValueError:
        return None


class Producer:
    def __init__(self):
        self.producer = create_producer()
        self._exec_producer = create_exec_report_producer()

    def send_trade(self, trade: Trade) -> None:
        data = {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "buy_order_id": trade.buy_order_id,
            "sell_order_id": trade.sell_order_id,
            "price": trade.price,
            "quantity": trade.quantity,
        }
        inject_ctx(data)
        self.producer.send("trades", data)

    def send_exec_reports(self, trade: Trade) -> None:
        """Emit one FIX Execution Report (ExecType=F) per side of the trade."""
        for order_id, client_id, side, order_qty, approved_at in [
            (
                trade.buy_order_id,
                trade.buy_client_id,
                "BUY",
                trade.buy_order_qty,
                trade.buy_approved_at,
            ),
            (
                trade.sell_order_id,
                trade.sell_client_id,
                "SELL",
                trade.sell_order_qty,
                trade.sell_approved_at,
            ),
        ]:
            try:
                report = ExecutionReportEvent(
                    order_id=order_id,
                    cl_ord_id=order_id,
                    client_id=client_id,
                    exec_type="F",
                    ord_status="2",
                    symbol=trade.symbol,
                    side=side,
                    price=trade.price,
                    order_qty=order_qty,
                    last_px=trade.price,
                    last_qty=trade.quantity,
                    leaves_qty=0,
                    cum_qty=trade.quantity,
                )
                with _tracer.start_as_current_span(
                    "matching-engine.send_exec_reports"
                ) as span:
                    span.set_attribute("exec_type", "F")
                    span.set_attribute("order.id", order_id)
                    span.set_attribute("order.side", side)
                    latency = _new_to_fill_latency_seconds(approved_at)
                    if latency is not None:
                        span.set_attribute("latency.new_to_fill_seconds", latency)
                        new_to_fill_latency_seconds.labels(side=side).observe(latency)
                    data = report.model_dump(mode="json")
                    inject_ctx(data)
                    self._exec_producer.send(_EXEC_REPORTS_TOPIC, data)
                    exec_reports_emitted.labels(
                        exec_type="F", service="matching-engine"
                    ).inc()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"failed to emit exec report (Fill) for order {order_id}: {exc}"
                )

    def send_book(self, book) -> None:

        snapshot = {
            "best_bid": book.best_bid().price if book.best_bid() else None,
            "best_ask": book.best_ask().price if book.best_ask() else None,
        }

        self.producer.send("order_book_updates", snapshot)
