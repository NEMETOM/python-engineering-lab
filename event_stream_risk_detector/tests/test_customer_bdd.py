# tests/test_customer_bdd.py

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from event_stream_risk_detector.rules import high_value_risk

pytestmark = pytest.mark.bdd

# Link the feature file
scenarios("features/risk.feature")


# Shared context for storing transaction info
@pytest.fixture
def context():
    return {}


# ------------------------
# GIVEN steps
# ------------------------
@given(parsers.parse("transaction with amount {amount:d}"))
def given_transaction(context, amount):
    """Store the transaction amount in context."""
    context["amount"] = amount


# ------------------------
# WHEN steps
# ------------------------
@when("event is evaluated")
def when_event_evaluated(context):
    """Compute whether the transaction is high value."""
    context["result"] = high_value_risk(context["amount"])


# ------------------------
# THEN steps
# ------------------------
@then(parsers.parse("high_value should be {expected}"))
def check_high_value(context, expected):
    """Assert that the high_value_risk result matches expectation."""
    high_value = context["result"]
    expected_bool = expected.lower() == "true"
    assert high_value == expected_bool
