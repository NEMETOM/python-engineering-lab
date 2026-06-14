Feature: Pre-trade risk checks

  Scenario Outline: Notional limit check approves orders within limit
    Given a risk checker with notional limit <limit>
    And an order for symbol "AAPL" side "BUY" price <price> quantity <qty>
    When the notional check runs
    Then the order is approved

    Examples:
      | limit     | price  | qty |
      | 1000000.0 | 100.0  | 100 |
      | 500000.0  | 99.0   | 10  |

  Scenario Outline: Notional limit check rejects orders above limit
    Given a risk checker with notional limit <limit>
    And an order for symbol "AAPL" side "BUY" price <price> quantity <qty>
    When the notional check runs
    Then the order is rejected
    And the rejection reason mentions "notional"

    Examples:
      | limit    | price   | qty  |
      | 500000.0 | 100.0   | 5001 |
      | 100000.0 | 50000.0 | 3    |

  Scenario Outline: Fat-finger check approves orders within threshold
    Given a risk checker with fat-finger threshold <pct>%
    And an order for symbol "BTCUSD" price <price>
    And the last trade price for "BTCUSD" is <last>
    When the fat-finger check runs
    Then the order is approved

    Examples:
      | pct  | price   | last    |
      | 10.0 | 100.0   | 95.0    |
      | 10.0 | 50000.0 | 48000.0 |

  Scenario Outline: Fat-finger check rejects orders outside threshold
    Given a risk checker with fat-finger threshold <pct>%
    And an order for symbol "BTCUSD" price <price>
    And the last trade price for "BTCUSD" is <last>
    When the fat-finger check runs
    Then the order is rejected
    And the rejection reason mentions "deviates"

    Examples:
      | pct  | price   | last    |
      | 10.0 | 150.0   | 100.0   |
      | 5.0  | 50000.0 | 40000.0 |

  Scenario Outline: Fat-finger check is skipped when no reference price exists
    Given a risk checker with fat-finger threshold 5.0%
    And an order for symbol "NEWTOKEN" price <price>
    And no last trade price exists for "NEWTOKEN"
    When the fat-finger check runs
    Then the order is approved

    Examples:
      | price   |
      | 99999.0 |
      | 1.0     |
