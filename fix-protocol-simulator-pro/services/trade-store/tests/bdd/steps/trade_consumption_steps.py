from datetime import datetime
from unittest.mock import MagicMock, patch

import trade_store.consumer  # noqa: F401  # ensure module is in sys.modules before patching
from behave import given, then, when
from trade_store.consumer import run


def _valid_msg_value(**overrides):
    defaults = dict(
        trade_id="T001",
        symbol="AAPL",
        buy_order_id="B001",
        sell_order_id="S001",
        price=150.0,
        quantity=10,
        timestamp=datetime.utcnow().isoformat(),
    )
    return {**defaults, **overrides}


@given("{count:d} valid trade messages")
def step_given_multiple_messages(context, count):
    msgs = []
    for i in range(count):
        msg = MagicMock()
        msg.value = _valid_msg_value(trade_id=f"T{i:03d}")
        msgs.append(msg)
    context.messages = msgs
    context.repo_side_effect = None


@given('a malformed trade message missing "{field}"')
def step_given_malformed_message(context, field):
    value = _valid_msg_value()
    del value[field]
    msg = MagicMock()
    msg.value = value
    context.messages = [msg]
    context.repo_side_effect = None


@given("the repository will fail on save")
def step_given_repo_fails(context):
    context.repo_side_effect = Exception("DB down")


def _run_pipeline(context):
    context.mock_repo = MagicMock()
    if getattr(context, "repo_side_effect", None):
        context.mock_repo.save.side_effect = context.repo_side_effect
    with patch("trade_store.consumer.create_consumer") as mock_create, patch(
        "trade_store.consumer.TradeRepository"
    ) as mock_repo_cls:
        mock_create.return_value = iter(context.messages)
        mock_repo_cls.return_value = context.mock_repo
        run()


@when("the pipeline processes the message")
def step_when_pipeline_single(context):
    _run_pipeline(context)


@when("the pipeline processes all messages")
def step_when_pipeline_all(context):
    _run_pipeline(context)


@then("{count:d} trade is stored")
def step_then_one_trade_stored(context, count):
    assert context.mock_repo.save.call_count == count


@then("{count:d} trades are stored")
def step_then_n_trades_stored(context, count):
    assert context.mock_repo.save.call_count == count


@then("the save was attempted and failed")
def step_then_save_attempted_and_failed(context):
    assert context.mock_repo.save.call_count == 1
    assert context.mock_repo.save.side_effect is not None
