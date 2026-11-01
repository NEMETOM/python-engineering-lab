import os
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# src as well as the repo root, so the suite runs without a prior pip install
# (same setup as market-data-service's tests/bdd/environment.py).
for _p in (_repo_root, _src):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ORD_STATUS = {"0": "0", "8": "8", "F": "2"}


class FakePipeline:
    """Stands in for everything between raw_orders and execution_reports.

    risk-service: one New (0) or Rejected (8) report per order.
    matching-engine: an accepted order fills against the first resting order
    on the opposite side with the same quantity and a crossing price, at the
    resting price. Partial fills are not modelled.

    The producer and consumer are what the patched KafkaProducer and
    KafkaConsumer classes return, so the shared factory code still runs.
    """

    def __init__(self) -> None:
        self.published: list[dict] = []
        self.pending: list[dict] = []
        self.rejects: dict[str, str] = {}
        self.silent = False
        self.topic_exists = True
        self._book: dict[str, list[dict]] = defaultdict(list)
        self._seq = 0

        self.producer = MagicMock()
        self.producer.send.side_effect = self._on_send
        self.consumer = MagicMock()
        self.consumer.partitions_for_topic.side_effect = lambda topic: (
            {0} if self.topic_exists else None
        )
        self.consumer.poll.side_effect = self._poll

    def reset_book(self) -> None:
        # Each run starts from a freshly reset pipeline, as the README asks
        # for when recording and comparing baselines.
        self._book.clear()
        self.pending.clear()

    def _on_send(self, topic: str, event: dict) -> None:
        assert topic == "raw_orders", f"published to {topic!r}"
        self.published.append(event)
        if self.silent:
            return
        self._seq += 1
        order = {**event, "order_id": f"oid-{self._seq}"}
        reason = self.rejects.get(order["symbol"])
        if reason is not None:
            self._report(order, "8", reason=reason)
            return
        self._report(order, "0")
        self._match(order)

    def _match(self, order: dict) -> None:
        resting = self._book[order["symbol"]]
        for other in resting:
            if other["side"] == order["side"] or other["quantity"] != order["quantity"]:
                continue
            buy, sell = (order, other) if order["side"] == "BUY" else (other, order)
            if buy["price"] < sell["price"]:
                continue
            resting.remove(other)
            for filled in (other, order):
                self._report(
                    filled,
                    "F",
                    last_px=other["price"],
                    last_qty=order["quantity"],
                )
            return
        resting.append(order)

    def _report(self, order: dict, exec_type: str, **kw) -> None:
        last_qty = kw.get("last_qty")
        self.pending.append(
            {
                "order_id": order["order_id"],
                "cl_ord_id": order["order_id"],
                "client_id": order["client_id"],
                "exec_type": exec_type,
                "ord_status": _ORD_STATUS[exec_type],
                "symbol": order["symbol"],
                "side": order["side"],
                "price": order["price"],
                "order_qty": order["quantity"],
                "last_px": kw.get("last_px"),
                "last_qty": last_qty,
                "leaves_qty": order["quantity"] if exec_type == "0" else 0,
                "cum_qty": last_qty or 0,
                "reason": kw.get("reason"),
            }
        )

    def _poll(self, timeout_ms: int = 0) -> dict:
        if not self.pending:
            time.sleep(0.005)  # a real poll blocks; don't spin the CPU
            return {}
        batch, self.pending = self.pending, []
        return {"execution_reports-0": [SimpleNamespace(value=v) for v in batch]}


def before_scenario(context, scenario):
    context.workdir = Path(tempfile.mkdtemp(prefix="fix-replay-bdd-"))
    context.fix_files = {}
    context.pipeline = FakePipeline()
    context.metrics_text = ""
    context.metrics_error = None


def after_scenario(context, scenario):
    shutil.rmtree(context.workdir, ignore_errors=True)
