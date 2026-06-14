Feature: Risk consumer pipeline

  Scenario Outline: Approved orders are forwarded to risk_approved_orders
    Given the risk pipeline is running
    And an order for symbol "<symbol>" passes all risk checks
    When the pipeline processes the order
    Then the approved topic receives 1 message
    And the rejected topic receives 0 messages

    Examples:
      | symbol |
      | AAPL   |
      | BTCUSD |

  Scenario Outline: Rejected orders are sent to risk_rejected_orders
    Given the risk pipeline is running with notional limit <limit>
    And an order with notional value above the limit
    When the pipeline processes the order
    Then the approved topic receives 0 messages
    And the rejected topic receives 1 message

    Examples:
      | limit |
      | 100.0 |
      | 50.0  |

  Scenario Outline: Trades update the last price reference
    Given the risk pipeline is running
    And a trade for symbol "<symbol>" at price <price>
    When the pipeline processes the trade
    Then the last price for "<symbol>" is <price>

    Examples:
      | symbol | price   |
      | AAPL   | 175.50  |
      | BTCUSD | 50000.0 |
