from behave import given, then, when
from playwright.sync_api import expect


def _rule_card(page, rule_id: str):
    return page.locator(f'[data-testid="rule-card"][data-rule-id="{rule_id}"]')


@given('the Compliance Rules page is open with "{rule_id}" active')
def step_rules_open(context, rule_id):
    context.page.goto("/admin/compliance")
    card = _rule_card(context.page, rule_id)
    expect(card.get_by_test_id("rule-badge")).to_have_text("Active")
    expect(card.get_by_role("switch")).to_have_attribute("aria-checked", "true")


@when('I switch "{rule_id}" off')
def step_switch_off(context, rule_id):
    _rule_card(context.page, rule_id).get_by_role("switch").click()


@then('"{rule_id}" shows as "{badge}"')
def step_rule_badge(context, rule_id, badge):
    card = _rule_card(context.page, rule_id)
    expect(card.get_by_test_id("rule-badge")).to_have_text(badge)
    checked = "true" if badge == "Active" else "false"
    expect(card.get_by_role("switch")).to_have_attribute("aria-checked", checked)


@then('the override for "{rule_id}" was saved as disabled')
def step_override_saved(context, rule_id):
    state = context.override_repo.state
    assert state.get(rule_id) is False, state


@then('after reloading the page "{rule_id}" still shows as "{badge}"')
def step_after_reload(context, rule_id, badge):
    context.page.reload()
    step_rule_badge(context, rule_id, badge)
