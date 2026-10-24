from dataclasses import dataclass, field
from pathlib import Path

_SOH = "\x01"
_PIPE = "|"

_SIDE_MAP = {"1": "BUY", "2": "SELL"}

_REQUIRED_TAGS = ("35", "55", "54", "44", "38")

# Logon, Heartbeat, Test Request, Logout: session-level, never reach raw_orders.
_SESSION_MSG_TYPES = {"A", "0", "1", "5"}


class InvalidLine(ValueError):
    """A line that the live pipeline would drop before risk-service sees it."""


@dataclass(frozen=True)
class ReplayOrder:
    source: str  # "<file>:<line>"
    client_id: str
    symbol: str
    side: str
    price: float
    quantity: int


@dataclass
class ParsedFiles:
    orders: list[ReplayOrder] = field(default_factory=list)
    session_messages: int = 0
    invalid: list[dict[str, str]] = field(default_factory=list)


def split_fields(raw: str) -> dict[str, str]:
    delimiter = _SOH if _SOH in raw else _PIPE
    fields: dict[str, str] = {}
    for part in raw.strip().split(delimiter):
        if "=" not in part:
            continue
        tag, value = part.split("=", 1)
        fields[tag] = value
    return fields


def parse_order(raw: str, source: str) -> ReplayOrder | None:
    """Parse one FIX line. Returns None for session messages.

    Validation mirrors what order-service drops (missing tags, non-positive
    price/quantity, unknown side), so every order that is sent is guaranteed
    to reach risk-service and produce exactly one New or Rejected report.
    """
    tags = split_fields(raw)

    if tags.get("35") in _SESSION_MSG_TYPES:
        return None

    missing = [tag for tag in _REQUIRED_TAGS if tag not in tags]
    if missing:
        raise InvalidLine(f"missing required tag(s): {', '.join(missing)}")

    if tags["35"] != "D":
        raise InvalidLine(f"unsupported message type 35={tags['35']!r}")

    side = _SIDE_MAP.get(tags["54"])
    if side is None:
        raise InvalidLine(f"unknown side 54={tags['54']!r}")

    try:
        price = float(tags["44"])
        quantity = int(tags["38"])
    except ValueError as exc:
        raise InvalidLine(f"non-numeric price/quantity: {exc}") from exc

    if price <= 0 or quantity <= 0:
        raise InvalidLine("price and quantity must be positive")

    return ReplayOrder(
        source=source,
        client_id=tags.get("49", "UNKNOWN"),
        symbol=tags["55"],
        side=side,
        price=price,
        quantity=quantity,
    )


def load_files(paths: list[Path]) -> ParsedFiles:
    """Parse files in the given order; line order within each file is kept."""
    parsed = ParsedFiles()
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                source = f"{path.name}:{line_no}"
                try:
                    order = parse_order(raw, source)
                except InvalidLine as exc:
                    parsed.invalid.append(
                        {"source": source, "raw": raw, "error": str(exc)}
                    )
                    continue
                if order is None:
                    parsed.session_messages += 1
                else:
                    parsed.orders.append(order)
    return parsed
