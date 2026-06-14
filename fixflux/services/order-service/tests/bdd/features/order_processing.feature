Feature: Order Processing Pipeline
  Valid raw orders are validated, transformed, and forwarded to the
  validated_orders topic. Orders that fail validation are silently
  dropped and an error is logged instead.

  Background:
    Given the order processing pipeline is initialised

  Scenario Outline: Valid orders are forwarded to the output topic
    Given a raw order with symbol "<symbol>", side "<side>", price <price>, quantity <quantity>
    When the pipeline processes the order
    Then 1 validated order is produced
    And the produced order has symbol "<symbol>"
    And the produced order has side "<side>"

    Examples:
      | symbol | side | price   | quantity |
      | AAPL   | BUY  | 100.0   | 10       |
      | TSLA   | SELL | 250.5   | 5        |
      | BTCUSD | BUY  | 50000.0 | 1        |

  Scenario Outline: Orders with invalid price are dropped
    Given a raw order with symbol "AAPL", side "BUY", price <price>, quantity 10
    When the pipeline processes the order
    Then 0 validated orders are produced

    Examples:
      | price |
      | 0.0   |
      | -10.0 |

  Scenario Outline: Orders with invalid quantity are dropped
    Given a raw order with symbol "AAPL", side "BUY", price 100.0, quantity <quantity>
    When the pipeline processes the order
    Then 0 validated orders are produced

    Examples:
      | quantity |
      | 0        |
      | -5       |

  Scenario Outline: Orders with invalid side are dropped
    Given a raw order with symbol "AAPL", side "<side>", price 100.0, quantity 10
    When the pipeline processes the order
    Then 0 validated orders are produced

    Examples:
      | side |
      | HOLD |
      | buy  |
