Feature: Position limit checks

  Scenario Outline: Orders within gross position limit are approved
    Given a risk checker with gross position limit <limit>
    And a flat position for client "CLIENT1" symbol "AAPL"
    And a position order for "CLIENT1" symbol "AAPL" side "<side>" quantity <qty>
    When the position check runs
    Then the order is approved

    Examples:
      | limit | side | qty  |
      | 10000 | BUY  | 5000 |
      | 10000 | SELL | 9999 |

  Scenario Outline: Orders breaching gross position limit are rejected
    Given a risk checker with gross position limit <limit>
    And a flat position for client "CLIENT1" symbol "AAPL"
    And a position order for "CLIENT1" symbol "AAPL" side "<side>" quantity <qty>
    When the position check runs
    Then the order is rejected
    And the rejection reason mentions "gross position"

    Examples:
      | limit | side | qty   |
      | 10000 | BUY  | 10001 |
      | 5000  | SELL | 5001  |

  Scenario Outline: Max open orders limit is enforced
    Given a risk checker with max open orders <max>
    And client "CLIENT2" has <existing> open orders
    And a new order from client "CLIENT2"
    When the open order count check runs
    Then the order is <outcome>

    Examples:
      | max | existing | outcome  |
      | 5   | 4        | approved |
      | 5   | 5        | rejected |

  Scenario Outline: Filled trades release open order slots
    Given a risk checker with max open orders 2
    And client "CLIENT3" has <initial> open orders
    When <filled> open orders are filled by trades
    Then client "CLIENT3" can place a new order: <can_place>

    Examples:
      | initial | filled | can_place |
      | 2       | 1      | true      |
      | 2       | 2      | true      |
