Feature: Trade Consumption Pipeline
  The consumer reads from the trades Kafka topic, deserializes each message
  into a TradeEvent and persists it via the repository.
  Malformed messages and repository failures are logged and skipped
  without crashing the consumer loop.

  Scenario Outline: Valid trade messages are stored
    Given a trade event with trade_id "<trade_id>", symbol "<symbol>", buy_order_id "<buy>", sell_order_id "<sell>", price <price>, quantity <quantity>
    When the pipeline processes the message
    Then 1 trade is stored

    Examples:
      | trade_id | symbol | buy  | sell | price   | quantity |
      | T001     | AAPL   | B001 | S001 | 150.0   | 10       |
      | T002     | MSFT   | B002 | S002 | 300.5   | 5        |
      | T003     | BTCUSD | B003 | S003 | 50000.0 | 1        |

  Scenario Outline: Multiple valid messages are each stored
    Given <count> valid trade messages
    When the pipeline processes all messages
    Then <count> trades are stored

    Examples:
      | count |
      | 2     |
      | 5     |

  Scenario Outline: Malformed messages are skipped without crashing
    Given a malformed trade message missing "<field>"
    When the pipeline processes the message
    Then 0 trades are stored

    Examples:
      | field    |
      | trade_id |
      | price    |
      | quantity |

  Scenario Outline: Repository failures do not crash the consumer
    Given a trade event with trade_id "<trade_id>", symbol "<symbol>", buy_order_id "<buy>", sell_order_id "<sell>", price <price>, quantity <quantity>
    And the repository will fail on save
    When the pipeline processes the message
    Then the save was attempted and failed

    Examples:
      | trade_id | symbol | buy  | sell | price  | quantity |
      | T001     | AAPL   | B001 | S001 | 150.0  | 10       |
      | T002     | TSLA   | B002 | S002 | 250.75 | 3        |
