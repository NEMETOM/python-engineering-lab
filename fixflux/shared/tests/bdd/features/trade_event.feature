Feature: TradeEvent Schema
  TradeEvent records a completed trade with both order IDs,
  price, quantity, and an auto-generated timestamp.

  Scenario Outline: Valid trade events are accepted
    Given a trade event with trade_id "<trade_id>", symbol "<symbol>", price <price>
    Then the trade event is valid
    And the trade event trade_id is "<trade_id>"

    Examples:
      | trade_id | symbol | price  |
      | T001     | AAPL   | 150.0  |
      | T002     | MSFT   | 300.5  |

  Scenario Outline: Missing required fields are rejected
    Given a trade event is missing the "<field>" field
    Then the trade event is invalid

    Examples:
      | field         |
      | trade_id      |
      | symbol        |
      | buy_order_id  |
      | sell_order_id |
      | price         |
      | quantity      |

  Scenario Outline: Invalid field types are rejected
    Given a trade event with an invalid "<field>" value "<value>"
    Then the trade event is invalid

    Examples:
      | field    | value        |
      | price    | not-a-number |
      | quantity | many         |
