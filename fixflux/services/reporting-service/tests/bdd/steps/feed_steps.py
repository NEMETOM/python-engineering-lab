import csv
import io
from datetime import UTC, datetime
from unittest.mock import MagicMock

from behave import given, then, when
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from reporting_service.api import main

RESTRICTED_MARKERS = ("lei", "client", "capacity", "buyer", "seller")


def _install_feed(context, fake):
    main.app.dependency_overrides[main._feed] = lambda: fake
    context.add_cleanup(main.app.dependency_overrides.clear)
    context.feed = fake


@given('the feed has a published trade in "{symbol}" at {price:g} for {quantity:d}')
def step_given_published_trade(context, symbol, price, quantity):
    fake = MagicMock()
    fake.fetch.return_value = [
        {
            "trade_id": f"T-{symbol}",
            "symbol": symbol,
            "asset_class": "equity",
            "price": price,
            "price_currency": "USD",
            "quantity": quantity,
            "trading_timestamp": datetime(2026, 11, 22, 11, 59, tzinfo=UTC),
            "reporting_timestamp": datetime(2026, 11, 22, 12, 0, tzinfo=UTC),
        }
    ]
    _install_feed(context, fake)


@given('the feed database is down with "{error}"')
def step_given_database_down(context, error):
    fake = MagicMock()
    fake.fetch.side_effect = OperationalError("SELECT", {}, Exception(error))
    _install_feed(context, fake)


@when('a client requests the post-trade feed as "{fmt}"')
def step_when_request_format(context, fmt):
    context.format = fmt
    context.response = TestClient(main.app).get(f"/post-trade?format={fmt}")


@when('a client requests the post-trade feed with "{query}"')
def step_when_request_query(context, query):
    context.response = TestClient(main.app).get(f"/post-trade?{query}")


def _trades(context) -> list[dict]:
    if context.format == "csv":
        return list(csv.DictReader(io.StringIO(context.response.text)))
    return context.response.json()["trades"]


@then("the response status is {status:d}")
def step_then_status(context, status):
    assert context.response.status_code == status, context.response.text


@then('the response has 1 trade in "{symbol}" at {price:g} for {quantity:d}')
def step_then_one_trade(context, symbol, price, quantity):
    trades = _trades(context)
    assert len(trades) == 1, trades
    assert trades[0]["symbol"] == symbol
    # CSV cells are text; JSON keeps numbers.
    assert float(trades[0]["price"]) == price
    assert int(trades[0]["quantity"]) == quantity


@then("no counterparty-identifying field is in the response")
def step_then_no_restricted_fields(context):
    keys = _trades(context)[0].keys()
    assert not [k for k in keys for m in RESTRICTED_MARKERS if m in k], keys


@then("the database was not queried")
def step_then_not_queried(context):
    context.feed.fetch.assert_not_called()


@then('the CSV symbol cell is "{cell}"')
def step_then_csv_cell(context, cell):
    assert _trades(context)[0]["symbol"] == cell


@then('the response does not mention "{error}"')
def step_then_no_leak(context, error):
    assert error not in context.response.text
