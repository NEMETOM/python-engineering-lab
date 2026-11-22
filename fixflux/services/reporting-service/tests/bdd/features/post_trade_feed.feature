Feature: RTS 1 public post-trade feed
  reporting-api publishes reportable trades at GET /post-trade as JSON or CSV,
  without authentication: post-trade transparency data is public. It never
  returns LEIs, client IDs or trading capacity, and rejects malformed input
  before it reaches the database.

  Scenario Outline: A published trade is returned in the requested format
    Given the feed has a published trade in "<symbol>" at <price> for <quantity>
    When a client requests the post-trade feed as "<format>"
    Then the response status is 200
    And the response has 1 trade in "<symbol>" at <price> for <quantity>
    And no counterparty-identifying field is in the response

    Examples:
      | symbol | price  | quantity | format |
      | AAPL   | 175.0  | 100      | json   |
      | MSFT   | 415.0  | 10       | json   |
      | AAPL   | 175.0  | 100      | csv    |
      | MSFT   | 415.0  | 10       | csv    |

  Scenario Outline: Malformed requests are rejected before the database
    Given the feed has a published trade in "AAPL" at 175.0 for 100
    When a client requests the post-trade feed with "<query>"
    Then the response status is 422
    And the database was not queried

    Examples:
      | query                         |
      | limit=0                       |
      | limit=1001                    |
      | format=xml                    |
      | since=2026-11-22T10:00:00     |
      | symbol=AAPL%27%3B%20DROP      |

  Scenario Outline: Spreadsheet formulas in symbols are neutralised in CSV
    Given the feed has a published trade in "<symbol>" at 1.0 for 1
    When a client requests the post-trade feed as "csv"
    Then the CSV symbol cell is "<cell>"

    Examples:
      | symbol        | cell           |
      | =HYPERLINK(1) | '=HYPERLINK(1) |
      | @SUM(1)       | '@SUM(1)       |
      | AAPL          | AAPL           |

  Scenario Outline: A database outage is a 503 that leaks nothing
    Given the feed database is down with "<error>"
    When a client requests the post-trade feed as "<format>"
    Then the response status is 503
    And the response does not mention "<error>"

    Examples:
      | error                               | format |
      | password authentication failed      | json   |
      | connection refused on postgres:5432 | csv    |
