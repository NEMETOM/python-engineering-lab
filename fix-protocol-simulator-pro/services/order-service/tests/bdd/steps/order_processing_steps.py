from unittest.mock import MagicMock, patch

from behave import given, then, when

from order_service.consumer import run


@given("the order processing pipeline is initialised")
def step_given_pipeline_init(context):
    context.mock_producer = MagicMock()


@when("the pipeline processes the order")
def step_when_pipeline_processes(context):
    msg = MagicMock()
    msg.value = context.msg_value

    with (
        patch("order_service.consumer.create_consumer") as mock_create_consumer,
        patch("order_service.consumer.Producer") as mock_producer_cls,
    ):
        mock_create_consumer.return_value = iter([msg])
        mock_producer_cls.return_value = context.mock_producer
        run()


@then("{count:d} validated order is produced")
def step_then_one_validated_order_produced(context, count):
    assert context.mock_producer.send.call_count == count


@then("{count:d} validated orders are produced")
def step_then_n_validated_orders_produced(context, count):
    assert context.mock_producer.send.call_count == count


@then('the produced order has symbol "{symbol}"')
def step_then_produced_symbol(context, symbol):
    args, _ = context.mock_producer.send.call_args
    assert args[0].symbol == symbol


@then('the produced order has side "{side}"')
def step_then_produced_side(context, side):
    args, _ = context.mock_producer.send.call_args
    assert args[0].side == side
