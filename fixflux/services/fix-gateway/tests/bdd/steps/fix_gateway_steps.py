# fixflux/services/fix-gateway/tests/bdd/steps/fix_gateway_steps.py

from datetime import datetime, timedelta

from behave import given, then, when  # type: ignore[import-untyped]

from fix_gateway.fix_handler import FixHandler
from fix_gateway.session_manager import SessionManager

# ---------------------------------------------------------------------------
# FixHandler steps
# ---------------------------------------------------------------------------


@given('a parsed FIX message with type "{msg_type}"')
def given_parsed_msg_type(context, msg_type):
    context.handler = FixHandler()
    context.msg = {"35": msg_type}


@then('the handler identifies it as "{label}"')
def then_handler_identifies(context, label):
    mapping = {
        "logon": context.handler.is_logon,
        "heartbeat": context.handler.is_heartbeat,
        "new order": context.handler.is_new_order,
    }
    assert mapping[label](
        context.msg
    ), f"Expected message to be identified as '{label}'"


@given('a raw FIX message "{raw}"')
def given_raw_fix_message(context, raw):
    context.handler = FixHandler()
    context.raw = raw


@when("the message is parsed")
def when_message_parsed(context):
    context.parsed = context.handler.parse(context.raw)


@then('the parsed field "{tag}" equals "{value}"')
def then_parsed_field_equals(context, tag, value):
    assert (
        context.parsed.get(tag) == value
    ), f"Expected tag {tag}='{value}', got '{context.parsed.get(tag)}'"


# ---------------------------------------------------------------------------
# SessionManager steps
# ---------------------------------------------------------------------------


@given("a session manager")
def given_session_manager(context):
    context.session_manager = SessionManager()


@given('a session already exists for sender "{sender}"')
def given_existing_session(context, sender):
    context.session_manager.create_session(sender)


@when('a logon is received from sender "{sender}"')
def when_logon_received(context, sender):
    context.session_manager.create_session(sender)


@when('a heartbeat is received from sender "{sender}"')
def when_heartbeat_received(context, sender):
    context.session_manager.update_heartbeat(sender)


@then('a session exists for "{sender}"')
def then_session_exists(context, sender):
    session = context.session_manager.get_session(sender)
    assert session is not None, f"Expected session for '{sender}' to exist"
    assert session.sender_comp_id == sender


@then('no session exists for "{sender}"')
def then_no_session_exists(context, sender):
    session = context.session_manager.get_session(sender)
    assert session is None, f"Expected no session for '{sender}'"


@then('the last heartbeat for "{sender}" is recent')
def then_heartbeat_is_recent(context, sender):
    session = context.session_manager.get_session(sender)
    assert session is not None, f"No session found for '{sender}'"
    delta = datetime.utcnow() - session.last_heartbeat
    assert delta < timedelta(seconds=5), f"Heartbeat timestamp is not recent: {delta}"
