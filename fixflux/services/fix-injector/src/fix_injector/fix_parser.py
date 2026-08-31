from datetime import datetime, timezone

_SOH = "\x01"
_PIPE = "|"

_SIDE_MAP = {"1": "BUY", "2": "SELL"}

_REQUIRED_TAGS = ("35", "55", "54", "44", "38")


class FixParseError(ValueError):
    """Raised when a raw FIX line isn't a valid New Order Single."""


def _split_fields(raw_message: str) -> dict:
    delimiter = _SOH if _SOH in raw_message else _PIPE
    fields: dict[str, str] = {}
    for field in raw_message.strip().split(delimiter):
        if "=" not in field:
            continue
        tag, value = field.split("=", 1)
        fields[tag] = value
    return fields


def parse_new_order_single(raw_message: str) -> dict:
    """Parse a raw FIX string (SOH- or pipe-delimited) into a New Order Single.

    Field mapping mirrors fix-filedrop-client's processor.py so an injected
    order lands on raw_orders in the exact shape order-service (RawOrderEvent)
    already expects from the real fix-gateway path.
    """
    tags = _split_fields(raw_message)

    missing = [tag for tag in _REQUIRED_TAGS if tag not in tags]
    if missing:
        raise FixParseError(f"missing required tag(s): {', '.join(missing)}")

    if tags["35"] != "D":
        raise FixParseError(
            f"only New Order Single (35=D) is supported, got 35={tags['35']!r}"
        )

    side = _SIDE_MAP.get(tags["54"])
    if side is None:
        raise FixParseError(f"unknown side 54={tags['54']!r} (expected 1=BUY, 2=SELL)")

    try:
        price = float(tags["44"])
        quantity = int(tags["38"])
    except ValueError as exc:
        raise FixParseError(f"non-numeric price/quantity: {exc}") from exc

    return {
        "msg_type": tags["35"],
        "client_order_id": tags.get("11"),
        "client_id": tags.get("49", "UNKNOWN"),
        "symbol": tags["55"],
        "side": side,
        "price": price,
        "quantity": quantity,
        "raw_tags": tags,
    }


def to_raw_order_event(parsed: dict) -> dict:
    """Shape a parsed order into raw_orders' schema (order_service.RawOrderEvent)."""
    return {
        "symbol": parsed["symbol"],
        "side": parsed["side"],
        "price": parsed["price"],
        "quantity": parsed["quantity"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_id": parsed["client_id"],
    }
