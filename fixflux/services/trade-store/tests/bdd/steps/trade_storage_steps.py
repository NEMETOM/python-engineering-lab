from unittest.mock import MagicMock, patch

from behave import given, then, when

from trade_store.repository import TradeRepository


@given("the database commit will fail")
def step_given_commit_fails(context):
    context.commit_should_fail = True


@when("the repository saves the trade")
def step_when_repo_saves(context):
    context.mock_session = MagicMock()
    with patch(
        "trade_store.repository.SessionLocal", return_value=context.mock_session
    ):
        TradeRepository().save(context.trade_event)


@when("the repository attempts to save the trade")
def step_when_repo_attempts(context):
    context.mock_session = MagicMock()
    if getattr(context, "commit_should_fail", False):
        context.mock_session.commit.side_effect = Exception("DB error")
    with patch(
        "trade_store.repository.SessionLocal", return_value=context.mock_session
    ):
        try:
            TradeRepository().save(context.trade_event)
        except Exception:
            pass


@then("the session add was called")
def step_then_session_add(context):
    context.mock_session.add.assert_called_once()


@then("the session commit was called")
def step_then_session_commit(context):
    context.mock_session.commit.assert_called_once()


@then("the session close was called")
def step_then_session_close(context):
    context.mock_session.close.assert_called_once()


@then('the stored trade has trade_id "{trade_id}"')
def step_then_stored_trade_id(context, trade_id):
    added = context.mock_session.add.call_args[0][0]
    assert added.trade_id == trade_id


@then('the stored trade has symbol "{symbol}"')
def step_then_stored_symbol(context, symbol):
    added = context.mock_session.add.call_args[0][0]
    assert added.symbol == symbol


@then("the stored trade has price {price:f}")
def step_then_stored_price(context, price):
    added = context.mock_session.add.call_args[0][0]
    assert added.price == price
