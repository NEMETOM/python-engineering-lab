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

  # ---------------------------------------------------------------------------
  # Risk-service gate: orders that exceed pre-trade limits are rejected
  # ---------------------------------------------------------------------------

  @needs_risk_service
  Scenario Outline: An order pair exceeding the notional cap is rejected before matching
    # Notional = price * qty; default cap is 1,000,000
    # Both sides exceed the cap so risk-service rejects them; no match occurs
    When a buy FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    And a sell FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    Then no trade for "<symbol>" appears in GET /trades within 15 seconds

    Examples:
      | symbol | price   | qty     |
      | AAPL   | 175.00  | 6000    |
      | EURUSD | 1.09000 | 1000000 |

  # ---------------------------------------------------------------------------
  # Compliance-service: trade size violations flagged by the observer
  # ---------------------------------------------------------------------------

  Scenario Outline: An order with excessive quantity triggers a trade size compliance violation
    # TradeSizeRule per-symbol limits: BTCUSD <= 100, default <= 10,000
    # Notional stays below 1,000,000 so risk-service approves the order
    When a buy FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    Then a compliance violation for rule "TradeSizeRule" appears in GET /violations within 20 seconds

    Examples:
      | symbol | price   | qty   |
      | BTCUSD | 1000.00 | 200   |
      | AAPL   | 5.00    | 15000 |

  # ---------------------------------------------------------------------------
  # Compliance-service: wash trading surveillance
  # ---------------------------------------------------------------------------

  Scenario Outline: Buy and sell from the same client on the same symbol triggers wash trading detection
    # WashTradingRule fires when the same client_id (E2E_CLIENT) submits
    # opposing sides for the same symbol within the 300-second window
    When a buy FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    And a sell FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    Then a trade for "<symbol>" appears in GET /trades within 30 seconds
    And a compliance violation for rule "WashTradingRule" appears in GET /violations within 20 seconds

    Examples:
      | symbol | price   | qty |
      | GBPUSD | 1.27000 | 50  |
      | MSFT   | 415.00  | 10  |

  # ---------------------------------------------------------------------------
  # Volume: prove the pipeline handles high-throughput order flow without loss
  # ---------------------------------------------------------------------------

  @volume
  Scenario Outline: FIXFlux processes high volumes of orders without message loss
    When <count> buy FIX orders for "<symbol>" at price <price> qty <qty> are dropped into the filedrop
    And <count> sell FIX orders for "<symbol>" at price <price> qty <qty> are dropped into the filedrop
    Then <count> trades for "<symbol>" appear in GET /trades within 120 seconds

    Examples:
      | symbol | count | price   | qty |
      | EURUSD | 1000  | 1.09000 | 100 |
      | AAPL   |  500  | 175.00  |  50 |
