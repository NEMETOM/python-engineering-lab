import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from calculator.price import apply_discount, add_vat

scenarios("features/price.feature")


@pytest.fixture
def context():
    return {}


@given(parsers.parse("the original price is {price:d}"))
def original_price(context, price):
    context["price"] = price


@when(parsers.parse("I apply a discount of {discount:d} percent"))
def apply_discount_step(context, discount):
    try:
        context["result"] = apply_discount(context["price"], discount)
    except Exception as e:
        context["error"] = e


@when(parsers.parse("I add VAT of {vat:d} percent"))
def add_vat_step(context, vat):
    try:
        context["result"] = add_vat(context["price"], vat)
    except Exception as e:
        context["error"] = e


@then(parsers.parse("the final price should be {expected:d}"))
def check_result(context, expected):
    import pytest
    assert context["result"] == pytest.approx(expected)


@then("a ValueError should be raised")
def check_error(context):
    assert isinstance(context.get("error"), ValueError)
