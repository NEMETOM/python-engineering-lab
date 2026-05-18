import uuid

from behave import then, when
from order_service.transformer import OrderTransformer


@when("the transformer processes the order")
def step_when_transformer_processes(context):
    transformer = OrderTransformer()
    context.validated = transformer.transform(context.raw_order)


@when("the transformer processes the order twice")
def step_when_transformer_processes_twice(context):
    transformer = OrderTransformer()
    context.validated_1 = transformer.transform(context.raw_order)
    context.validated_2 = transformer.transform(context.raw_order)


@then('the validated order has symbol "{symbol}"')
def step_then_validated_symbol(context, symbol):
    assert context.validated.symbol == symbol


@then('the validated order has side "{side}"')
def step_then_validated_side(context, side):
    assert context.validated.side == side


@then("the validated order has price {price:f}")
def step_then_validated_price(context, price):
    assert context.validated.price == price


@then("the validated order has quantity {quantity:d}")
def step_then_validated_quantity(context, quantity):
    assert context.validated.quantity == quantity


@then("the validated order ID is a valid UUID")
def step_then_order_id_is_uuid(context):
    uuid.UUID(context.validated.order_id)


@then("the two order IDs are different")
def step_then_order_ids_different(context):
    assert context.validated_1.order_id != context.validated_2.order_id
