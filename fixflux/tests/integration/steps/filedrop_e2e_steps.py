import sys
import tempfile
import time
from pathlib import Path

from behave import then, when

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
