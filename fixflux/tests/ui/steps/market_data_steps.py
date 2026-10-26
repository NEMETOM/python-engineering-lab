import json

from behave import given, then, when
from playwright.sync_api import expect


def _make_snapshot(**overrides):
    defaults = {
        "symbol": "AAPL",
        "best_bid": 174.9,
        "best_ask": 175.1,
        "mid_price": 175.0,
        "last_trade_price": 175.0,
        "timestamp": "2026-10-26T12:00:00Z",
    }
    return {**defaults, **overrides}


@given("the Market Data page is open and the stream is live")
def step_market_data_live(context):
    context.page.goto("/market-data")
    # The page's WebSocket is intercepted by route_web_socket (environment.py),
    # so "live" means the page opened it and the mock accepted it.
    expect(context.page.locator("#status")).to_have_text("live")
    expect(context.page.locator("#empty")).to_be_visible()
    assert len(context.ws_routes) == 1, "page did not open its market data socket"


@when('a snapshot for "{symbol}" with bid {bid:g} and ask {ask:g} arrives')
def step_snapshot_arrives(context, symbol, bid, ask):
    snapshot = _make_snapshot(
        symbol=symbol,
        best_bid=bid,
        best_ask=ask,
        mid_price=(bid + ask) / 2,
        last_trade_price=bid,
    )
    context.ws_routes[0].send(json.dumps(snapshot))


@then(
    'the "{symbol}" row shows bid "{bid_text}", ask "{ask_text}" and mid "{mid_text}"'
)
def step_row_values(context, symbol, bid_text, ask_text, mid_text):
    row = context.page.locator(f'[data-testid="quote-row"][data-symbol="{symbol}"]')
    expect(row.get_by_test_id("cell-symbol")).to_have_text(symbol)
    expect(row.get_by_test_id("cell-bid")).to_have_text(bid_text)
    expect(row.get_by_test_id("cell-ask")).to_have_text(ask_text)
    expect(row.get_by_test_id("cell-mid")).to_have_text(mid_text)


@then("the waiting message is hidden")
def step_waiting_hidden(context):
    expect(context.page.locator("#empty")).to_be_hidden()
    expect(context.page.locator("#quotes")).to_be_visible()


@then('the update counter reads "{text}"')
def step_update_counter(context, text):
    expect(context.page.locator("#msg-count")).to_have_text(text)
