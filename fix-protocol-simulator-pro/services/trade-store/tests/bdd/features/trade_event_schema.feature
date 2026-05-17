Feature: Trade Event Schema
  TradeEvent validates all required fields at construction time.
  Missing or wrongly-typed fields raise a ValidationError immediately.

  Scenario Outline: Valid trade events are accepted
    Given a trade event with trade_id "<trade_id>", symbol "<symbol>", buy_order_id "<buy>", sell_order_id "<sell>", price <price>, quantity <quantity>
    Then the trade event is valid
    And the trade event has symbol "<symbol>"
    And the trade event has price <price>

    Examples:
      | trade_id | symbol | buy  | sell | price   | quantity |
      | T001     | AAPL   | B001 | S001 | 150.0   | 10       |
      | T002     | MSFT   | B002 | S002 | 300.5   | 5        |
      | T003     | BTCUSD | B003 | S003 | 50000.0 | 1        |
      | T004     | EURUSD | B004 | S004 | 1.08    | 100      |

  Scenario Outline: Trade events with a missing required field are rejected
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

  Scenario Outline: Trade events with an invalid field type are rejected
    Given a trade event has an invalid "<field>" value of "<value>"
    Then the trade event is invalid

    Examples:
      | field     | value        |
      | price     | not-a-number |
      | quantity  | many         |
      | timestamp | not-a-date   |
