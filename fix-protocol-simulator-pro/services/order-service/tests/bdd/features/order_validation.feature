Feature: Order Validation
  The validator enforces business rules: price and quantity must be positive
  and side must be BUY or SELL. Any violation raises a clear error.

  Scenario Outline: Valid orders pass validation
    Given a raw order with symbol "<symbol>", side "<side>", price <price>, quantity <quantity>
    When the validator processes the order
    Then the order is accepted

    Examples:
      | symbol | side | price   | quantity |
      | AAPL   | BUY  | 100.0   | 10       |
      | BTCUSD | SELL | 50000.0 | 1        |
      | EURUSD | BUY  | 1.08    | 100      |
      | TSLA   | SELL | 250.5   | 5        |

  Scenario Outline: Orders with invalid price are rejected
    Given a raw order with symbol "AAPL", side "BUY", price <price>, quantity 10
    When the validator processes the order
    Then the order is rejected with message "price must be positive"

    Examples:
      | price  |
      | 0.0    |
      | -1.0   |
      | -100.0 |

  Scenario Outline: Orders with invalid quantity are rejected
    Given a raw order with symbol "AAPL", side "BUY", price 100.0, quantity <quantity>
    When the validator processes the order
    Then the order is rejected with message "quantity must be positive"

    Examples:
      | quantity |
      | 0        |
      | -1       |
      | -50      |

  Scenario Outline: Orders with invalid side are rejected
    Given a raw order with symbol "AAPL", side "<side>", price 100.0, quantity 10
    When the validator processes the order
    Then the order is rejected with message "invalid side"

    Examples:
      | side  |
      | HOLD  |
      | buy   |
      | sell  |
      | SHORT |
