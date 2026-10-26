from behave import given, then, when
from playwright.sync_api import expect

from pages import ConsolePage


@given('I open the FixFlux Console at "{path}"')
def step_open_console(context, path):
    context.page.goto(path)


@when('I click the "{tab}" tab')
def step_click_tab(context, tab):
    ConsolePage(context.page).nav.open_tab(tab)


@then('the "{tab}" tab is the active tab')
def step_tab_active(context, tab):
    nav = ConsolePage(context.page).nav
    expect(nav.tab(tab)).to_have_attribute("aria-current", "page")
    # Exactly one tab may claim to be the current page.
    expect(nav.current_tabs).to_have_count(1)


@then('the page heading reads "{heading}"')
def step_heading(context, heading):
    expect(ConsolePage(context.page).heading).to_have_text(heading)
