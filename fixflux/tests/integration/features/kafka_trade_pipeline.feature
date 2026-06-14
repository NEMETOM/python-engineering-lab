@integration
@needs_kafka
Feature: Kafka Trade Pipeline Integration
  Verify that trade events published to the Kafka trades topic are consumed
  and persisted to PostgreSQL by the trade-store consumer pipeline.

  Background:
    Given the trades table is empty

  Scenario Outline: A valid trade event published to Kafka is persisted to the database
    Given a valid trade message for symbol "<symbol>" at price <price> and quantity <quantity> is published to the trades topic
    When the consumer pipeline processes available messages
    Then the expected trade for symbol "<symbol>" at price <price> is in the database

    Examples:
      | symbol  | price    | quantity |
      | BTCUSD  | 50000.00 | 1        |
      | ETHUSD  | 3000.00  | 5        |
      | AAPL    | 175.50   | 25       |

  Scenario Outline: A malformed message is skipped and the next valid message is still stored
    Given a malformed message is published to the trades topic
    And a valid trade message for symbol "<symbol>" at price <price> and quantity 1 is published to the trades topic
    When the consumer pipeline processes available messages
    Then the expected trade for symbol "<symbol>" is in the database
    And the malformed message was handled without crashing the pipeline

    Examples:
      | symbol  | price    |
      | BTCUSD  | 50000.00 |
      | AAPL    | 175.50   |
