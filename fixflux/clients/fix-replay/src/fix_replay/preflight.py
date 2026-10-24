import re
import urllib.request

_BOOK_LINE = re.compile(
    r'^orders_in_book\{(?=[^}]*side="(?P<side>[^"]+)")'
    r'(?=[^}]*symbol="(?P<symbol>[^"]+)")[^}]*\}\s+(?P<value>\S+)$'
)


def resting_orders(metrics_text: str, symbols: set[str]) -> dict[str, int]:
    """Resting order count per symbol (both sides) from matching-engine's
    /metrics, limited to the given symbols and omitting empty books."""
    counts: dict[str, int] = {}
    for line in metrics_text.splitlines():
        match = _BOOK_LINE.match(line.strip())
        if not match or match["symbol"] not in symbols:
            continue
        counts[match["symbol"]] = counts.get(match["symbol"], 0) + int(
            float(match["value"])
        )
    return {symbol: n for symbol, n in sorted(counts.items()) if n > 0}


def fetch_metrics(url: str, timeout_s: float = 3.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout_s) as resp:  # noqa: S310
        return resp.read().decode("utf-8")
