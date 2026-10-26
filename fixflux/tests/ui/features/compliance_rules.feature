Feature: Compliance Rules
  Each compliance and surveillance rule can be switched off live from the
  Console. The change is saved as an override and survives a page reload.

  Scenario Outline: Switching a rule off takes effect and is saved
    Given the Compliance Rules page is open with "<rule_id>" active
    When I switch "<rule_id>" off
    Then "<rule_id>" shows as "Disabled"
    And the override for "<rule_id>" was saved as disabled
    And after reloading the page "<rule_id>" still shows as "Disabled"

    Examples:
      | rule_id           |
      | wash_trading      |
      | missing_client_id |
