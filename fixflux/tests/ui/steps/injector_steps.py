from behave import given, then, when
from playwright.sync_api import expect

# Prices at the levels the sample data uses, so the orders look realistic.
_PRICES = {"AAPL": "175.00", "MSFT": "415.00", "EURUSD": "1.09000"}


def _make_fix_line(symbol: str, index: int) -> str:
    side = "1" if index % 2 == 0 else "2"
    return (
        f"8=FIX.4.2|35=D|49=UI_CLIENT_{index}|55={symbol}|54={side}|40=2|"
        f"44={_PRICES[symbol]}|38=100|"
    )


@given("the Fix Msg Injector page is open")
def step_injector_open(context):
    context.page.goto("/")


@when('I paste {count:d} valid New Order Single lines for "{symbol}" and submit')
def step_paste_and_submit(context, count, symbol):
    lines = "\n".join(_make_fix_line(symbol, i) for i in range(count))
    context.page.locator("#raw_text").fill(lines)
    context.page.locator("#submit").click()


@then('the injector status reads "{text}"')
def step_status(context, text):
    expect(context.page.locator("#status")).to_have_text(text)


@then("{count:d} results are marked as published")
def step_results_published(context, count):
    results = context.page.locator("#results")
    expect(results.get_by_text("PUBLISHED", exact=True)).to_have_count(count)


@then('{count:d} orders for "{symbol}" were sent to raw_orders')
def step_orders_sent(context, count, symbol):
    events = context.producer.events
    assert len(events) == count, events
    assert all(e["symbol"] == symbol for e in events), events
