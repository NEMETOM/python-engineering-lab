@integration
Feature: Trade Persistence
  Verify that trades are durably stored in PostgreSQL and are queryable
  through both the repository layer and the REST API.

  Background:
    Given the trades table is empty

  Scenario Outline: A saved trade is retrievable by ID via the API
    Given a trade "<trade_id>" for symbol "<symbol>" at price <price> and quantity <quantity>
    When the trade is saved via the repository
    And GET /trades/<trade_id> is called
    Then the response status is 200
    And the response body contains symbol "<symbol>", price <price>, quantity <quantity>

    Examples:
      | trade_id  | symbol  | price    | quantity |
      | T-INT-001 | BTCUSD  | 50000.00 | 1        |
      | T-INT-002 | ETHUSD  | 3000.00  | 10       |
      | T-INT-003 | AAPL    | 175.50   | 100      |
      | T-INT-004 | MSFT    | 420.00   | 50       |

  Scenario Outline: GET /trades filters results by symbol
    Given these trades exist in the database:
      | trade_id  | symbol  | price    | quantity |
      | T-F-001   | BTCUSD  | 50000.00 | 1        |
      | T-F-002   | BTCUSD  | 49000.00 | 2        |
      | T-F-003   | ETHUSD  | 3000.00  | 5        |
    When GET /trades?symbol=<symbol> is called
    Then the response status is 200
    And the response contains exactly <count> trades
    And all returned trades have symbol "<symbol>"

    Examples:
      | symbol  | count |
      | BTCUSD  | 2     |
      | ETHUSD  | 1     |

  Scenario: GET /trades with no symbol filter returns all trades
    Given these trades exist in the database:
      | trade_id  | symbol  | price    | quantity |
      | T-A-001   | BTCUSD  | 50000.00 | 1        |
      | T-A-002   | ETHUSD  | 3000.00  | 5        |
      | T-A-003   | AAPL    | 175.50   | 10       |
    When GET /trades is called
    Then the response status is 200
    And the response contains exactly 3 trades

  Scenario: GET /trades/{trade_id} returns 404 for an unknown ID
    When GET /trades/DOES-NOT-EXIST is called
    Then the response status is 404
