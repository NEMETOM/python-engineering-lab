from behave import given, then, when
from playwright.sync_api import expect

from pages import ComplianceRulesPage


def _expect_rule_state(page: ComplianceRulesPage, rule_id: str, badge: str) -> None:
    rule = page.rule(rule_id)
    expect(rule.badge).to_have_text(badge)
    checked = "true" if badge == "Active" else "false"
    expect(rule.switch).to_have_attribute("aria-checked", checked)


@given('the Compliance Rules page is open with "{rule_id}" active')
def step_rules_open(context, rule_id):
    context.rules = ComplianceRulesPage(context.page).open()
    _expect_rule_state(context.rules, rule_id, "Active")


@when('I switch "{rule_id}" off')
def step_switch_off(context, rule_id):
    context.rules.rule(rule_id).toggle()


@then('"{rule_id}" shows as "{badge}"')
def step_rule_badge(context, rule_id, badge):
    _expect_rule_state(context.rules, rule_id, badge)


@then('the override for "{rule_id}" was saved as disabled')
def step_override_saved(context, rule_id):
    state = context.override_repo.state
    assert state.get(rule_id) is False, state


@then('after reloading the page "{rule_id}" still shows as "{badge}"')
def step_after_reload(context, rule_id, badge):
    context.rules.reload()
    _expect_rule_state(context.rules, rule_id, badge)
