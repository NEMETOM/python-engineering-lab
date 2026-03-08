# src/event_stream_risk_detector/rules.py


def high_value_risk(amount: float, threshold: float = 10000.0) -> bool:
    """Return True if transaction exceeds threshold."""
    return amount >= threshold


def blocked_country_risk(country: str, blocked_countries: list[str]) -> bool:
    """Return True if country is blocked."""
    return country in blocked_countries


def velocity_risk(transaction_times: list[float], max_tx: int = 5) -> bool:
    """Return True if transaction count exceeds allowed velocity."""
    return len(transaction_times) > max_tx


def device_risk(device_id: str, trusted_devices: list[str]) -> bool:
    """Return True if device is not trusted."""
    return device_id not in trusted_devices


def geo_velocity_risk(
    previous_country: str,
    current_country: str,
    time_diff_minutes: float,
    min_travel_time: float = 60,
) -> bool:
    """Return True if travel between countries is unrealistically fast."""
    if previous_country != current_country and time_diff_minutes < min_travel_time:
        return True
    return False
