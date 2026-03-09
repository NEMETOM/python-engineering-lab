# tests/test_rules.py
import pytest

from event_stream_risk_detector.rules import blocked_country_risk, high_value_risk


@pytest.mark.parametrize(
    "amount, expected",
    [
        (15000, True),
        (500, False),
        (10000, True),  # boundary
        (0, False),
        (-100, False),
    ],
)
def test_high_value_risk(amount: float, expected: bool) -> None:
    result = high_value_risk(amount)
    assert result == expected


@pytest.mark.parametrize(
    "country, blocked, expected",
    [
        ("IR", ["IR", "KP"], True),
        ("KP", ["IR", "KP"], True),
        ("GB", ["IR", "KP"], False),
        ("US", [], False),
    ],
)
def test_blocked_country_risk(country: str, blocked: list[str], expected: bool) -> None:
    result = blocked_country_risk(country, blocked)
    assert result == expected


@pytest.mark.parametrize(
    "times, expected",
    [
        ([1, 2, 3], False),
        ([1, 2, 3, 4, 5, 6], True),
    ],
)
def test_velocity_risk(times: list[float], expected: bool) -> None:
    from event_stream_risk_detector.rules import velocity_risk

    assert velocity_risk(times) == expected


@pytest.mark.parametrize(
    "device, trusted, expected",
    [
        ("iphone", ["iphone", "laptop"], False),
        ("android", ["iphone", "laptop"], True),
    ],
)
def test_device_risk(device: str, trusted: list[str], expected: bool) -> None:
    from event_stream_risk_detector.rules import device_risk

    assert device_risk(device, trusted) == expected


@pytest.mark.parametrize(
    "prev_country, curr_country, time_diff, expected",
    [
        ("UK", "UK", 10, False),
        ("UK", "JP", 10, True),
        ("UK", "JP", 120, False),
    ],
)
def test_geo_velocity_risk(
    prev_country: str,
    curr_country: str,
    time_diff: float,
    expected: bool,
) -> None:
    from event_stream_risk_detector.rules import geo_velocity_risk

    assert geo_velocity_risk(prev_country, curr_country, time_diff) == expected
