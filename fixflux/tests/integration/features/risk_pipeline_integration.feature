@integration @needs_kafka @needs_risk_service
Feature: Risk Service Pre-Trade Checks (Integration)
  The risk-service consumes validated_orders, applies four MiFID II-aligned
  pre-trade checks, and routes each order to either risk_approved_orders
  (pass) or risk_rejected_orders (fail).

  Requires: Kafka/Redpanda + risk-service running.
  Start with: docker compose --profile full up

  # ── Notional cap ───────────────────────────────────────────────────────────

  Scenario Outline: Orders within the notional cap are approved
    Given a unique risk test client is created
    And a validated order for the test client symbol "<symbol>" side "BUY" price <price> qty <qty>
    When the order is published to validated_orders
    Then the order appears in risk_approved_orders within 10 seconds

    Examples:
      | symbol | price  | qty |
      | AAPL   | 100.00 | 100 |
      | MSFT   | 50.00  | 500 |

  Scenario Outline: Orders that breach the notional cap are rejected
    Given a unique risk test client is created
    And a validated order for the test client symbol "<symbol>" side "BUY" price <price> qty <qty>
    When the order is published to validated_orders
    Then the order appears in risk_rejected_orders within 10 seconds
    And the rejection reason contains "notional"

    Examples:
      | symbol | price    | qty  |
      | BTCUSD | 50000.00 | 25   |
      | AAPL   | 175.00   | 6000 |

  # ── Fat-finger check ────────────────────────────────────────────────────────

  Scenario Outline: Orders on symbols with no trade history pass the fat-finger check
    Given a unique risk test client is created
    And a validated order for the test client symbol "<symbol>" side "BUY" price <price> qty <qty>
    When the order is published to validated_orders
    Then the order appears in risk_approved_orders within 10 seconds

    Examples:
      | symbol      | price  | qty |
      | COLDSTART1  | 100.00 | 10  |
      | COLDSTART2  | 200.00 | 5   |

  Scenario Outline: Orders that deviate more than 10 percent from the last trade price are rejected
    Given a trade for "<symbol>" at price <ref_price> has been processed by the risk service
    And a unique risk test client is created
    And a validated order for the test client symbol "<symbol>" side "BUY" price <order_price> qty 10
    When the order is published to validated_orders
    Then the order appears in risk_rejected_orders within 10 seconds
    And the rejection reason contains "deviates"

    Examples:
      | symbol  | ref_price | order_price |
      | FFTEST1 | 400.00    | 445.00      |
      | FFTEST2 | 100.00    | 115.00      |

  # ── Position limits ─────────────────────────────────────────────────────────

  Scenario Outline: Orders that stay within both position limits are approved
    Given a unique risk test client is created
    And a validated order for the test client symbol "<symbol>" side "BUY" price <price> qty <qty>
    When the order is published to validated_orders
    Then the order appears in risk_approved_orders within 10 seconds

    Examples:
      | symbol | price | qty  |
      | EURUSD | 1.09  | 5000 |
      | GBPUSD | 1.27  | 4000 |

  Scenario Outline: Orders that would push gross position over the cap are rejected
    Given a unique risk test client is created
    And a validated order for the test client symbol "<symbol>" side "BUY" price <price> qty <qty>
    When the order is published to validated_orders
    Then the order appears in risk_rejected_orders within 10 seconds
    And the rejection reason contains "gross position"

    Examples:
      | symbol | price | qty   |
      | EURUSD | 1.09  | 10001 |
      | GBPUSD | 1.27  | 10001 |

  Scenario Outline: Orders that would push net position over the cap are rejected
    Given a unique risk test client is created
    And a validated order for the test client symbol "<symbol>" side "BUY" price <price> qty <qty>
    When the order is published to validated_orders
    Then the order appears in risk_rejected_orders within 10 seconds
    And the rejection reason contains "net position"

    Examples:
      | symbol | price | qty  |
      | EURUSD | 1.09  | 5001 |
      | GBPUSD | 1.27  | 5001 |

  # ── Max open orders ─────────────────────────────────────────────────────────

  Scenario Outline: The eleventh open order for a client is rejected
    Given a unique risk test client is created
    And 10 open orders for the test client on "<symbol>" have been approved by the risk service
    And a validated order for the test client symbol "<symbol>" side "BUY" price 10.00 qty 1
    When the order is published to validated_orders
    Then the order appears in risk_rejected_orders within 15 seconds
    And the rejection reason contains "open order count"

    Examples:
      | symbol |
      | AAPL   |
      | MSFT   |

  Scenario Outline: Open order limit does not affect a different client
    Given a unique risk test client is created
    And 10 open orders for the test client on "<symbol>" have been approved by the risk service
    And a second unique risk test client is created
    And a validated order for the second test client symbol "<symbol>" side "BUY" price 10.00 qty 1
    When the order is published to validated_orders
    Then the order appears in risk_approved_orders within 10 seconds

    Examples:
      | symbol |
      | AAPL   |
      | MSFT   |
