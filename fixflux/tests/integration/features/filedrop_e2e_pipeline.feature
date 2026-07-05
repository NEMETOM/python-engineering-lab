@e2e
@needs_full_stack
Feature: FIXFlux End-to-End Order Pipeline
  Demonstrates the complete lifecycle of a trading order through the FIXFlux
  pipeline - from a raw FIX message dropped as a file, all the way to a
  matched trade visible through the REST API.

  The pipeline under test:

    Client (FIX file)
      └─► FIX Gateway     - parses the protocol message
            └─► Order Service  - validates business rules and assigns an order ID
                  └─► Risk Service   - enforces MiFID II pre-trade checks (notional, fat-finger, limits)
                        └─► Matching Engine  - matches buy against sell at best price-time priority
                              └─► Trade Store  - persists the trade to PostgreSQL
                                    └─► REST API   - exposes matched trades at GET /trades

  Each scenario below exercises a distinct behaviour of this pipeline.
  Requires the full Docker stack:  docker compose --profile full up

  Background:
    Given the trades table is empty

  # ---------------------------------------------------------------------------
  # Golden path - the complete order lifecycle, start to finish
  # ---------------------------------------------------------------------------

  @golden-path
  Scenario Outline: A buy and sell order cross - the trade flows end-to-end and appears via REST
    A trader submits a buy and a matching sell for the same instrument at the
    same price. The pipeline validates, risk-checks, matches, and persists the
    resulting trade - which immediately becomes queryable via the Trade Store API.
    A logon and heartbeat are sent first to mirror a realistic FIX session lifecycle,
    populating all three message types in the Grafana message distribution panel.

    When a FIX logon is dropped into the filedrop
    And a FIX heartbeat is dropped into the filedrop
    And a trader submits a buy order for <qty> units of "<symbol>" at a limit price of <price>
    And  a matching sell order for <qty> units of "<symbol>" at <price> enters the pipeline
    Then the matched trade for "<symbol>" is recorded and visible in the Trade Store within 30 seconds

    Examples:
      | symbol | price   | qty |
      | EURUSD | 1.09000 | 100 |
      | AAPL   | 175.00  | 50  |

  # ---------------------------------------------------------------------------
  # Resilience - malformed messages are quarantined, not lost or blocking
  # ---------------------------------------------------------------------------

  Scenario Outline: A malformed FIX message is quarantined to the dead-letter topic without blocking valid orders
    The gateway isolates any message it cannot parse and routes it to a
    dead-letter topic. Subsequent valid orders are unaffected and still produce
    matched trades - no single bad message can stall the pipeline.

    When an invalid FIX message "<raw_line>" is dropped into the filedrop
    And a buy FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    And a sell FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    Then a trade for "<symbol>" appears in GET /trades within 30 seconds

    Examples:
      | raw_line                                      | symbol | price  | qty |
      | 8=FIX.4.2\|35=D\|49=BAD\|55=EURUSD\|54=2\|   | EURUSD | 1.0900 | 200 |
      | NOT_A_FIX_MESSAGE                             | AAPL   | 176.00 | 25  |

  # ---------------------------------------------------------------------------
  # MiFID II pre-trade risk gate - oversized orders stopped before matching
  # ---------------------------------------------------------------------------

  @needs_risk_service
  Scenario Outline: An oversized order is blocked by the MiFID II notional cap before reaching the matching engine
    The risk service enforces a notional cap (price x quantity) of 1,000,000.
    Orders that exceed this threshold are rejected outright - they never reach
    the matching engine and no trade is produced.

    When a buy FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    And a sell FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    Then no trade for "<symbol>" appears in GET /trades within 15 seconds

    Examples:
      | symbol | price   | qty     |
      | AAPL   | 175.00  | 6000    |
      | EURUSD | 1.09000 | 1000000 |

  # ---------------------------------------------------------------------------
  # Compliance surveillance - trade size violations flagged by the observer
  # ---------------------------------------------------------------------------

  Scenario Outline: An order breaching the per-symbol size limit triggers a compliance violation
    The compliance service passively observes every order. When a quantity
    exceeds the per-symbol limit (BTCUSD: 100, default: 10,000) a TradeSizeRule
    violation is recorded - even if risk-service approved the order on notional.
    A non-crossing sell at a higher price is submitted alongside the buy so that
    both sides of the order book carry resting orders (visible in Grafana's
    Order Book Depth panel for symbols where qty passes the risk position limit).

    When a buy FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    And a sell FIX order for "<symbol>" at price <sell_price> qty <qty> is dropped into the filedrop
    Then a compliance violation for rule "TradeSizeRule" appears in GET /violations within 20 seconds

    Examples:
      | symbol | price   | sell_price | qty   |
      | BTCUSD | 1000.00 | 1040.00    | 200   |
      | MSFT   | 50.00   | 52.00      | 15000 |

  # ---------------------------------------------------------------------------
  # Compliance surveillance - wash trading detection
  # ---------------------------------------------------------------------------

  Scenario Outline: Opposing orders from the same client on the same instrument trigger wash trading surveillance
    Submitting a buy and sell for the same symbol from the same client within
    the 300-second surveillance window is flagged as potential wash trading.
    The trade still executes - the compliance service is a passive observer,
    not a blocker - but the violation is recorded and queryable.

    When a buy FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    And a sell FIX order for "<symbol>" at price <price> qty <qty> is dropped into the filedrop
    Then a trade for "<symbol>" appears in GET /trades within 30 seconds
    And a compliance violation for rule "WashTradingRule" appears in GET /violations within 20 seconds

    Examples:
      | symbol | price   | qty |
      | GBPUSD | 1.27000 | 50  |
      | MSFT   | 415.00  | 10  |

  # ---------------------------------------------------------------------------
  # Compliance - missing client ID
  # ---------------------------------------------------------------------------

  Scenario: An order with no client ID triggers a MissingClientIdRule compliance violation
    The compliance service applies MissingClientIdRule first in its chain.
    Any order where the sender comp ID (tag 49) is absent is flagged immediately.
    The order still flows through the pipeline - compliance is a passive observer.

    When a buy FIX order with no client ID for "USDJPY" at price 149.50 qty 100 is dropped into the filedrop
    Then a compliance violation for rule "MissingClientIdRule" appears in GET /violations within 20 seconds

  # ---------------------------------------------------------------------------
  # Compliance - invalid symbol
  # ---------------------------------------------------------------------------

  Scenario: An order for an unrecognised instrument triggers an InvalidSymbolRule compliance violation
    The compliance service checks every order against the configured symbol allowlist.
    An unknown instrument is flagged - the order still reaches the matching engine
    (compliance observes but does not block), but it will never match a counterpart.

    When a buy FIX order for "UNKNWN" at price 100.00 qty 10 is dropped into the filedrop
    Then a compliance violation for rule "InvalidSymbolRule" appears in GET /violations within 20 seconds

  # ---------------------------------------------------------------------------
  # Compliance - duplicate order detection
  # ---------------------------------------------------------------------------

  Scenario: Submitting the same order twice triggers a DuplicateOrderRule compliance violation
    The compliance service uses client_id + symbol + side + price + quantity as the
    deduplication key. Resending an identical order within the detection window is
    flagged as a potential operational error or replay attack.

    When a buy FIX order for "NFLX" at price 600.00 qty 5 is dropped into the filedrop
    And  a buy FIX order for "NFLX" at price 600.00 qty 5 is dropped into the filedrop
    Then a compliance violation for rule "DuplicateOrderRule" appears in GET /violations within 20 seconds

  # ---------------------------------------------------------------------------
  # Pre-trade - fat-finger check
  # ---------------------------------------------------------------------------

  @needs_risk_service
  Scenario: A price deviating more than 10% from the last matched trade is blocked by the fat-finger check
    The risk service tracks the last trade price per symbol. Any new order priced
    more than 10% away from that reference is rejected before reaching the matching
    engine. A crossing pair is submitted first to establish the reference price,
    then a buy at 3400 is sent - 13% above the 3000 reference - triggering the check.

    When a buy FIX order for "ETHUSD" at price 3000.00 qty 1 is dropped into the filedrop
    And  a sell FIX order for "ETHUSD" at price 3000.00 qty 1 is dropped into the filedrop
    Then the matched trade for "ETHUSD" is recorded and visible in the Trade Store within 30 seconds
    When a buy FIX order for "ETHUSD" at price 3400.00 qty 1 is dropped into the filedrop
    Then a risk rejection for "ETHUSD" appears within 15 seconds

  # ---------------------------------------------------------------------------
  # Volume - prove the pipeline handles high-throughput order flow without loss
  # ---------------------------------------------------------------------------

  @volume
  Scenario Outline: The pipeline processes high-volume order flow without message loss
    Submits a large batch of crossing orders to verify that no messages are
    dropped under load. Every buy is matched with a sell and the full count of
    trades must appear in the Trade Store within the timeout.

    When <count> buy FIX orders for "<symbol>" at price <price> qty <qty> are dropped into the filedrop
    And <count> sell FIX orders for "<symbol>" at price <price> qty <qty> are dropped into the filedrop
    Then <count> trades for "<symbol>" appear in GET /trades within 120 seconds

    Examples:
      | symbol | count | price   | qty |
      | EURUSD | 1000  | 1.09000 | 100 |
      | AAPL   |  500  | 175.00  |  50 |
