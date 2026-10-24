from types import SimpleNamespace

_ORD_STATUS = {"0": "0", "8": "8", "F": "2"}


def exec_report(client_id, exec_type="0", reason=None, last_qty=None, **kw):
    """A consumer record wrapping an execution_reports payload."""
    order_id = kw.get("order_id", "oid")
    value = {
        "order_id": order_id,
        "cl_ord_id": order_id,
        "client_id": client_id,
        "exec_type": exec_type,
        "ord_status": _ORD_STATUS[exec_type],
        "symbol": kw.get("symbol", "AAPL"),
        "side": kw.get("side", "BUY"),
        "price": kw.get("price", 175.5),
        "order_qty": kw.get("order_qty", 100),
        "last_px": kw.get("last_px"),
        "last_qty": last_qty,
        "leaves_qty": 0,
        "cum_qty": last_qty or 0,
        "reason": reason,
    }
    return SimpleNamespace(value=value)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakeConsumer:
    """poll() returns one queued batch per call and advances the clock."""

    def __init__(self, clock, batches, step=1.0):
        self.clock = clock
        self.batches = list(batches)
        self.step = step

    def poll(self, timeout_ms):
        self.clock.now += self.step
        records = self.batches.pop(0) if self.batches else []
        return {"tp": records} if records else {}
