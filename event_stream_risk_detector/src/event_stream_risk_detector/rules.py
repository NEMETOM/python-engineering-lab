# src/event_stream_risk_detector/rules.py


def high_value_risk(amount: float, threshold: float = 10000.0) -> bool:
    """Return True if transaction exceeds threshold."""
    return amount >= threshold


def blocked_country_risk(country: str, blocked_countries: list[str]) -> bool:
    """Return True if country is blocked."""
    return country in blocked_countries
