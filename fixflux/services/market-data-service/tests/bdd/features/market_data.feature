Feature: Market data cache and publisher
  market-data-service keeps the latest best bid, best ask and last trade price
  per symbol, from order_book_updates and trades. It publishes a snapshot to the
  market_data topic only when a symbol's quote actually changes.

  Scenario Outline: A symbol with no market data has no snapshot
    Given a fresh market cache
    Then there is no snapshot for "<symbol>"

    Examples:
      | symbol |
      | AAPL   |
      | EURUSD |

  Scenario Outline: A trade sets the symbol's last trade price
    Given a fresh market cache
    When a trade for "<symbol>" at <price> is received
    Then the last trade price for "<symbol>" is <price>

    Examples:
      | symbol | price   |
      | AAPL   | 175.00  |
      | EURUSD | 1.09    |
      | BTCUSD | 50010.0 |

  Scenario Outline: A later trade overwrites the earlier price
    Given a fresh market cache
    When a trade for "<symbol>" at <first_price> is received
    And a trade for "<symbol>" at <second_price> is received
    Then the last trade price for "<symbol>" is <second_price>

    Examples:
      | symbol | first_price | second_price |
      | AAPL   | 175.00      | 176.50       |
      | EURUSD | 1.0901      | 1.0899       |

  Scenario Outline: An order book update sets the best bid and ask
    Given a fresh market cache
    When an order book update for "<symbol>" with bid <bid> and ask <ask> is received
    Then the best bid for "<symbol>" is <bid>
    And the best ask for "<symbol>" is <ask>

    Examples:
      | symbol | bid    | ask    |
      | AAPL   | 174.90 | 175.10 |
      | EURUSD | 1.0899 | 1.0901 |

  Scenario Outline: A later order book update overwrites the earlier one
    Given a fresh market cache
    When an order book update for "<symbol>" with bid <first_bid> and ask <first_ask> is received
    And an order book update for "<symbol>" with bid <second_bid> and ask <second_ask> is received
    Then the best bid for "<symbol>" is <second_bid>
    And the best ask for "<symbol>" is <second_ask>

    Examples:
      | symbol | first_bid | first_ask | second_bid | second_ask |
      | MSFT   | 414.80    | 415.20    | 414.90     | 415.10     |
      | GBPUSD | 1.2699    | 1.2701    | 1.2700     | 1.2702     |

  Scenario Outline: The mid price is the midpoint of a two-sided book
    Given a fresh market cache
    When an order book update for "<symbol>" with bid <bid> and ask <ask> is received
    Then the mid price for "<symbol>" is <mid>

    Examples:
      | symbol | bid    | ask    | mid    |
      | AAPL   | 174.90 | 175.10 | 175.00 |
      | ETHUSD | 2999.0 | 3001.0 | 3000.0 |

  Scenario Outline: A one-sided book has no mid price
    # matching-engine sends null for the side of the book that is empty.
    Given a fresh market cache
    When an order book update for "<symbol>" with bid <bid> and ask <ask> is received
    Then the best bid for "<symbol>" is <bid>
    And the best ask for "<symbol>" is <ask>
    And the mid price for "<symbol>" is absent

    Examples:
      | symbol | bid    | ask    |
      | EURUSD | 1.0915 | none   |
      | AAPL   | none   | 175.10 |

  Scenario Outline: A trade before any order book update has no mid price
    Given a fresh market cache
    When a trade for "<symbol>" at <price> is received
    Then the mid price for "<symbol>" is absent
    And the best bid for "<symbol>" is none

    Examples:
      | symbol | price  |
      | AAPL   | 175.00 |
      | MSFT   | 415.00 |

  Scenario Outline: Symbols are tracked independently
    # The reason the cache is keyed by symbol: one instrument's prices must
    # never leak into another's snapshot.
    Given a fresh market cache
    When a trade for "<traded>" at <price> is received
    And an order book update for "<quoted>" with bid <bid> and ask <ask> is received
    Then the last trade price for "<traded>" is <price>
    And the best bid for "<traded>" is none
    And the last trade price for "<quoted>" is none
    And the best bid for "<quoted>" is <bid>

    Examples:
      | traded | price  | quoted | bid    | ask    |
      | AAPL   | 175.00 | EURUSD | 1.0899 | 1.0901 |
      | BTCUSD | 50010  | MSFT   | 414.80 | 415.20 |

  Scenario Outline: The publisher sends each symbol's snapshot to market_data
    Given a fresh market cache
    And a market data publisher
    When a trade for "<symbol>" at <price> is received
    And an order book update for "<symbol>" with bid <bid> and ask <ask> is received
    And the publisher publishes
    Then 1 snapshot is sent to the "market_data" topic
    And the sent snapshot for "<symbol>" has bid <bid>, ask <ask> and last trade price <price>

    Examples:
      | symbol | price  | bid    | ask    |
      | AAPL   | 175.00 | 174.90 | 175.10 |
      | EURUSD | 1.09   | 1.0899 | 1.0901 |

  Scenario Outline: A snapshot is only re-sent when the quote changes
    # The Market Data tab relies on this: a repeated trade at the same price
    # with an unchanged book produces no new message.
    Given a fresh market cache
    And a market data publisher
    When a trade for "AAPL" at 175.00 is received
    And the publisher publishes
    And a trade for "AAPL" at <second_price> is received
    And the publisher publishes
    Then <sent> snapshot(s) are sent to the "market_data" topic

    Examples:
      | second_price | sent |
      | 175.00       | 1    |
      | 176.00       | 2    |
