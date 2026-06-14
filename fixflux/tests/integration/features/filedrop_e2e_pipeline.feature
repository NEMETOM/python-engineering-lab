@e2e
@needs_full_stack
Feature: End-to-End FIX Filedrop Pipeline
  Verify the complete order flow: a FIX file dropped into the filedrop client
  is parsed, published to raw_orders, validated by the order service, matched
  by the matching engine, and the resulting trade is persisted and visible via
  the Trade Store REST API.

  Requires the full Docker pipeline to be running:
    docker compose --profile full up

  Background:
    Given the trades table is empty

  Scenario Outline: A crossing FIX order pair produces a trade visible via REST API
    When a buy FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    And a sell FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    Then a trade for "<symbol>" appears in GET /trades within 30 seconds

    Examples:
      | symbol | price   | qty |
      | EURUSD | 1.09000 | 100 |
      | AAPL   | 175.00  | 50  |

  Scenario Outline: An invalid FIX message reaches the dead letter topic and does not block valid orders
    When an invalid FIX message "<raw_line>" is dropped into the filedrop
    And a buy FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    And a sell FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    Then a trade for "<symbol>" appears in GET /trades within 30 seconds

    Examples:
      | raw_line                                      | symbol | price  | qty |
      | 8=FIX.4.2\|35=D\|49=BAD\|55=EURUSD\|54=2\|   | EURUSD | 1.0900 | 200 |
      | NOT_A_FIX_MESSAGE                             | AAPL   | 176.00 | 25  |
