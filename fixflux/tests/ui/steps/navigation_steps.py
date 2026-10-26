from behave import given, then, when
from playwright.sync_api import expect


@given('I open the FixFlux Console at "{path}"')
def step_open_console(context, path):
    context.page.goto(path)


@when('I click the "{tab}" tab')
def step_click_tab(context, tab):
    context.page.get_by_role("navigation").get_by_role("link", name=tab).click()


@then('the "{tab}" tab is the active tab')
def step_tab_active(context, tab):
    nav = context.page.get_by_role("navigation")
    expect(nav.get_by_role("link", name=tab)).to_have_attribute("aria-current", "page")
    # Exactly one tab may claim to be the current page.
    expect(nav.locator('[aria-current="page"]')).to_have_count(1)


@then('the page heading reads "{heading}"')
def step_heading(context, heading):
    expect(context.page.get_by_role("heading", level=1)).to_have_text(heading)
