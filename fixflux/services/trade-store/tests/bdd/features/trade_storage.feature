Feature: Trade Storage
  The TradeRepository maps TradeEvent fields onto a TradeModel and persists it.
  The DB session lifecycle (add, commit, close) is always correctly managed,
  including when a commit raises an exception.

  Scenario Outline: Valid trades are persisted with all fields mapped correctly
    Given a trade event with trade_id "<trade_id>", symbol "<symbol>", buy_order_id "<buy>", sell_order_id "<sell>", price <price>, quantity <quantity>
    When the repository saves the trade
    Then the session add was called
    And the session commit was called
    And the session close was called
    And the stored trade has trade_id "<trade_id>"
    And the stored trade has symbol "<symbol>"
    And the stored trade has price <price>

    Examples:
      | trade_id | symbol | buy  | sell | price  | quantity |
      | T001     | AAPL   | B001 | S001 | 150.0  | 10       |
      | T002     | MSFT   | B002 | S002 | 300.5  | 5        |
      | T003     | TSLA   | B003 | S003 | 250.75 | 2        |

  Scenario Outline: Session is closed even when commit fails
    Given a trade event with trade_id "<trade_id>", symbol "<symbol>", buy_order_id "<buy>", sell_order_id "<sell>", price <price>, quantity <quantity>
    And the database commit will fail
    When the repository attempts to save the trade
    Then the session close was called

    Examples:
      | trade_id | symbol | buy  | sell | price  | quantity |
      | T001     | AAPL   | B001 | S001 | 150.0  | 10       |
      | T002     | MSFT   | B002 | S002 | 300.5  | 5        |
