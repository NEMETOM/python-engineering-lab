#tests/features/risk.feature

Feature: Event Risk Detection

  Scenario: High value transaction
    Given transaction with amount 15000
    When event is evaluated
    Then high_value should be True

  Scenario: Low value transaction
    Given transaction with amount 500
    When event is evaluated
    Then high_value should be False