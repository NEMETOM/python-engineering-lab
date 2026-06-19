import os
import sys
import tempfile
import time
from pathlib import Path

import httpx
from behave import then, when

_COMPLIANCE_URL = os.getenv("COMPLIANCE_URL", "http://localhost:8010")

_here = Path(__file__).resolve()
_repo_root = _here.parent.parent.parent.parent  # fixflux/
_filedrop_dir = _repo_root / "clients" / "fix-filedrop-client"
_fix_gateway_src = _repo_root / "services" / "fix-gateway" / "src"

for _p in (str(_filedrop_dir), str(_fix_gateway_src)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _write_and_process(raw_line: str) -> None:
    """Write a single-line FIX file to the filedrop and process it immediately."""
    from processor import FileProcessor

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        dir=_filedrop_dir / "filedrop",
        delete=False,
        prefix="e2e_",
    ) as f:
        f.write(raw_line + "\n")
        tmp_path = Path(f.name)

    processor = FileProcessor()
    processor.process(tmp_path)
    processor.producer.flush()


def _write_batch_and_process(lines: list) -> None:
    """Write a multi-line FIX file to the filedrop and process it in one shot."""
    from processor import FileProcessor

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        dir=_filedrop_dir / "filedrop",
        delete=False,
        prefix="e2e_vol_",
    ) as f:
        for line in lines:
            f.write(line + "\n")
        tmp_path = Path(f.name)

    processor = FileProcessor()
    processor.process(tmp_path)
    processor.producer.flush()


@when(
    'a buy FIX order for "{symbol}" at price {price:f} qty {qty:d} is dropped into the filedrop'
)
def step_drop_buy(context, symbol, price, qty):
    _write_and_process(
        f"8=FIX.4.2|35=D|49=E2E_CLIENT|55={symbol}|54=1|40=2|44={price:.5f}|38={qty}|"
    )


@when(
    'a sell FIX order for "{symbol}" at price {price:f} qty {qty:d} is dropped into the filedrop'
)
def step_drop_sell(context, symbol, price, qty):
    _write_and_process(
        f"8=FIX.4.2|35=D|49=E2E_CLIENT|55={symbol}|54=2|40=2|44={price:.5f}|38={qty}|"
    )


@when('an invalid FIX message "{raw_line}" is dropped into the filedrop')
def step_drop_invalid(context, raw_line):
    _write_and_process(raw_line)


@then('no trade for "{symbol}" appears in GET /trades within {timeout:d} seconds')
def step_no_trade_appears(context, symbol, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = context.api_client.get(f"/trades?symbol={symbol}")
        assert (
            response.status_code == 200
        ), f"GET /trades returned HTTP {response.status_code}: {response.text}"
        if response.json():
            raise AssertionError(
                f"Trade for {symbol!r} appeared but should have been rejected by risk-service."
            )
        time.sleep(2)
    # Full timeout elapsed with no trade - assertion passes


@then('a compliance violation for rule "{rule}" appears in GET /violations within {timeout:d} seconds')
def step_violation_appears(context, rule, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = httpx.get(
                f"{_COMPLIANCE_URL}/violations",
                params={"rule_name": rule, "limit": 10},
                timeout=5.0,
            )
            if response.status_code == 200 and response.json():
                return
        except Exception:
            pass
        time.sleep(2)
    raise AssertionError(
        f"No violation for rule '{rule}' appeared in GET /violations within {timeout}s.\n"
        "Is the compliance service running?  docker compose --profile full up"
    )


@then('a trade for "{symbol}" appears in GET /trades within {timeout:d} seconds')
def step_trade_appears(context, symbol, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = context.api_client.get(f"/trades?symbol={symbol}")
        assert (
            response.status_code == 200
        ), f"GET /trades returned HTTP {response.status_code}: {response.text}"
        if response.json():
            return
        time.sleep(2)
    raise AssertionError(
        f"No trade for {symbol!r} appeared in GET /trades within {timeout}s.\n"
        "Is the full pipeline running?  docker compose --profile full up"
    )


@when('{count:d} buy FIX orders for "{symbol}" at price {price:f} qty {qty:d} are dropped into the filedrop')
def step_drop_bulk_buy(context, count, symbol, price, qty):
    # Each order gets a unique client ID so no single client ever accumulates
    # more than one open order, staying well clear of RISK_MAX_OPEN_ORDERS=10.
    lines = [
        f"8=FIX.4.2|35=D|49=E2E_VOL_B{i:04d}|55={symbol}|54=1|40=2|44={price:.5f}|38={qty}|"
        for i in range(count)
    ]
    _write_batch_and_process(lines)


@when('{count:d} sell FIX orders for "{symbol}" at price {price:f} qty {qty:d} are dropped into the filedrop')
def step_drop_bulk_sell(context, count, symbol, price, qty):
    # Sell-side client IDs are distinct from buy-side to avoid WashTradingRule
    # detections; matching engine pairs orders by symbol+price, not client ID.
    lines = [
        f"8=FIX.4.2|35=D|49=E2E_VOL_S{i:04d}|55={symbol}|54=2|40=2|44={price:.5f}|38={qty}|"
        for i in range(count)
    ]
    _write_batch_and_process(lines)


@then('{count:d} trades for "{symbol}" appear in GET /trades within {timeout:d} seconds')
def step_n_trades_appear(context, count, symbol, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = context.api_client.get(f"/trades?symbol={symbol}")
        assert (
            response.status_code == 200
        ), f"GET /trades returned HTTP {response.status_code}: {response.text}"
        found = len(response.json())
        if found >= count:
            return
        time.sleep(5)
    response = context.api_client.get(f"/trades?symbol={symbol}")
    found = len(response.json()) if response.status_code == 200 else 0
    raise AssertionError(
        f"Expected {count} trades for {symbol!r} but found {found} after {timeout}s.\n"
        "Is the full pipeline running?  docker compose --profile full up"
    )
