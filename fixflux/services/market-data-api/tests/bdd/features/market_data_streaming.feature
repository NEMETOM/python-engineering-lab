Feature: Real-time market data over WebSocket
  market-data-api consumes the market_data Kafka topic on a background thread
  and pushes every valid snapshot to all clients connected to /ws/market-data.
  Malformed messages are skipped without stopping the stream, and a client that
  goes away never blocks delivery to the others.

  Background:
    Given the market data API is running

  Scenario Outline: Every connected client receives each snapshot
    Given <clients> WebSocket clients are connected
    When market data for "<symbol>" with bid <bid> and ask <ask> is published
    Then every client receives a snapshot for "<symbol>" with mid price <mid>

    Examples:
      | clients | symbol | bid     | ask     | mid      |
      | 1       | AAPL   | 175.0   | 175.5   | 175.25   |
      | 3       | EURUSD | 1.0898  | 1.0902  | 1.09     |
      | 2       | BTCUSD | 64000.0 | 64010.0 | 64005.0  |

  Scenario Outline: One-sided books stream with a null side and no mid price
    Given 1 WebSocket clients are connected
    When market data for "<symbol>" with bid <bid> and ask <ask> is published
    Then every client receives a snapshot for "<symbol>" with mid price null
    And the snapshot has best bid <bid> and best ask <ask>

    Examples:
      | symbol | bid   | ask   |
      | MSFT   | 415.0 | null  |
      | MSFT   | null  | 415.5 |

  Scenario Outline: Malformed messages are skipped and the stream continues
    Given 2 WebSocket clients are connected
    When a market data message missing "<field>" is published
    And market data for "<next>" with bid 100.0 and ask 101.0 is published
    Then the first snapshot every client receives is for "<next>"

    Examples:
      | field     | next   |
      | symbol    | AAPL   |
      | timestamp | ETHUSD |
      | best_bid  | MSFT   |

  Scenario Outline: Clients that disconnect stop being tracked and never block the rest
    Given <clients> WebSocket clients are connected
    When <leaving> of the clients disconnect
    Then the API tracks <remaining> connections
    When market data for "AAPL" with bid 175.0 and ask 175.5 is published
    Then every client receives a snapshot for "AAPL" with mid price 175.25

    Examples:
      | clients | leaving | remaining |
      | 2       | 1       | 1         |
      | 4       | 3       | 1         |

  Scenario Outline: Health is reported independently of streaming clients
    Given <clients> WebSocket clients are connected
    Then GET /health returns status "ok" for service "market-data-api"

    Examples:
      | clients |
      | 0       |
      | 2       |

  Scenario Outline: The consumer uses the shared factory's Kafka settings
    Then the Kafka consumer subscribes to "market_data" with <setting> set to "<value>"

    Examples:
      | setting            | value           |
      | group_id           | market-data-api |
      | auto_offset_reset  | earliest        |
      | enable_auto_commit | True            |
