# tests/test_rules.py
import pytest

from event_stream_risk_detector.rules import high_value_risk


@pytest.mark.parametrize(
    "amount, expected",
    [
        (15000, True),  # high value
        (500, False),  # low value
        (10000, True),  # boundary/high value (depending on your logic)
        (0, False),  # edge case: zero
        (-100, False),  # edge case: negative value
    ],
)
def test_high_value_risk(amount, expected):
    result = high_value_risk(amount)
    assert result == expected
