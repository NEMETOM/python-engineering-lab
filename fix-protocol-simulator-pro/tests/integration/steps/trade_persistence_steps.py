from datetime import datetime, timezone

from behave import given, then, when


def _make_trade_event(trade_id, symbol, price, quantity):
    from trade_store.schemas import TradeEvent

    return TradeEvent(
        trade_id=trade_id,
        symbol=symbol,
        buy_order_id=f"B-{trade_id}",
        sell_order_id=f"S-{trade_id}",
        price=float(price),
        quantity=int(quantity),
        timestamp=datetime.now(timezone.utc),
    )


# ── Givens ────────────────────────────────────────────────────────────────────


@given("the trades table is empty")
def step_trades_table_empty(context):
    pass  # guaranteed by before_scenario hook in environment.py


@given(
    'a trade "{trade_id}" for symbol "{symbol}" at price {price:f} and quantity {quantity:d}'
)
def step_given_single_trade(context, trade_id, symbol, price, quantity):
    context.trade_event = _make_trade_event(trade_id, symbol, price, quantity)


@given("these trades exist in the database")
def step_given_table_of_trades(context):
    from trade_store.repository import TradeRepository

    repo = TradeRepository()
    for row in context.table:
        repo.save(
            _make_trade_event(
                row["trade_id"],
                row["symbol"],
                float(row["price"]),
                int(row["quantity"]),
            )
        )


# ── Whens ─────────────────────────────────────────────────────────────────────


@when("the trade is saved via the repository")
def step_when_save(context):
    from trade_store.repository import TradeRepository

    TradeRepository().save(context.trade_event)


@when("GET /trades/{trade_id} is called")
def step_when_get_by_id(context, trade_id):
    context.response = context.api_client.get(f"/trades/{trade_id}")


@when("GET /trades?symbol={symbol} is called")
def step_when_get_filtered(context, symbol):
    context.response = context.api_client.get(f"/trades?symbol={symbol}")


@when("GET /trades is called")
def step_when_get_all(context):
    context.response = context.api_client.get("/trades")


# ── Thens ─────────────────────────────────────────────────────────────────────


@then("the response status is {status:d}")
def step_then_status(context, status):
    assert context.response.status_code == status, (
        f"Expected HTTP {status}, got {context.response.status_code}: "
        f"{context.response.text}"
    )


@then(
    'the response body contains symbol "{symbol}", price {price:f}, quantity {quantity:d}'
)
def step_then_body_fields(context, symbol, price, quantity):
    body = context.response.json()
    assert body["symbol"] == symbol, f"symbol: expected {symbol!r}, got {body['symbol']!r}"
    assert abs(body["price"] - price) < 0.001, (
        f"price: expected {price}, got {body['price']}"
    )
    assert body["quantity"] == quantity, (
        f"quantity: expected {quantity}, got {body['quantity']}"
    )


@then("the response contains exactly {count:d} trades")
def step_then_trade_count(context, count):
    body = context.response.json()
    assert isinstance(body, list), f"Expected list, got {type(body).__name__}: {body}"
    assert len(body) == count, f"Expected {count} trade(s), got {len(body)}"


@then('all returned trades have symbol "{symbol}"')
def step_then_all_symbol(context, symbol):
    for trade in context.response.json():
        assert trade["symbol"] == symbol, (
            f"Expected symbol {symbol!r}, got {trade['symbol']!r}"
        )
