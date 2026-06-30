@chaos
@needs_full_stack
Feature: FIXFlux Chaos Recovery - Matching Engine Resilience
  Proves that Kafka durability guarantees are real: orders submitted while
  the matching engine is offline are not lost. When the engine restarts it
  replays from its last committed offset and every queued order is matched.

  The failure scenario under test:

    Client (FIX file)
      └─► FIX Gateway ──► Order Service ──► Risk Service
                                                  │
                                            risk_approved_orders
                                            (Kafka - durable log)
                                                  │
                                           [matching-engine DOWN]
                                                  │
                                           [matching-engine UP]
                                                  │
                                            Matching Engine ──► Trade Store

  Requires the full Docker stack:  docker compose --profile full up

  Background:
    Given the trades table is empty

  # ---------------------------------------------------------------------------
  # Scenario A - matching engine killed, orders survive in Kafka, replayed on restart
  # ---------------------------------------------------------------------------

  Scenario Outline: Orders queued in Kafka while the matching engine is down are all matched after recovery
    The matching engine is the sole consumer of the risk_approved_orders topic.
    Stopping it mid-pipeline does not lose messages - Kafka retains them at the
    last committed offset. When the engine restarts it replays every unconsumed
    message and produces the expected trades.

    Given the "matching-engine" container is stopped
    When <count> buy FIX orders for "<symbol>" at price <price> qty <qty> are dropped into the filedrop
    And  <count> sell FIX orders for "<symbol>" at price <price> qty <qty> are dropped into the filedrop
    And  the "matching-engine" container is restarted
    Then <count> trades for "<symbol>" appear in GET /trades within <timeout> seconds

    Examples:
      | symbol | count | price   | qty | timeout |
      | EURUSD | 5     | 1.09000 | 100 | 60      |
      | AAPL   | 3     | 175.00  |  50 | 60      |
