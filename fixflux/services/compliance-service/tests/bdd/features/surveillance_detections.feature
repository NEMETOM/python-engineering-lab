Feature: Surveillance Pattern Detection
  The surveillance engine detects multi-event patterns that indicate market
  manipulation or disruptive trading behaviour.

  Scenario Outline: Wash trading detected when same client trades both sides
    Given a wash trading rule with a 300-second window
    When client "<client>" submits a "<side1>" then a "<side2>" order for "<symbol>"
    Then the wash trading alert is "<outcome>"

    Examples:
      | client  | side1 | side2 | symbol | outcome   |
      | CLIENT1 | BUY   | SELL  | EURUSD | triggered |
      | CLIENT1 | SELL  | BUY   | EURUSD | triggered |
      | CLIENT1 | BUY   | BUY   | EURUSD | not fired |
      | CLIENT1 | BUY   | SELL  | BTCUSD | triggered |

  Scenario Outline: Rapid-fire orders detected when burst exceeds threshold
    Given a rapid fire rule allowing <limit> orders per 60 seconds
    When client "CLIENT1" submits <count> orders within the window
    Then the rapid fire alert is "<outcome>"

    Examples:
      | limit | count | outcome   |
      | 10    | 10    | not fired |
      | 10    | 11    | triggered |
      | 5     | 6     | triggered |
      | 5     | 4     | not fired |

  Scenario Outline: Repeated identical orders trigger suspicious pattern alert
    Given a repeated orders rule with threshold <threshold>
    When client "CLIENT1" submits the same order <count> times
    Then the repeated orders alert is "<outcome>"

    Examples:
      | threshold | count | outcome   |
      | 3         | 2     | not fired |
      | 3         | 3     | triggered |
      | 5         | 4     | not fired |
      | 5         | 5     | triggered |
