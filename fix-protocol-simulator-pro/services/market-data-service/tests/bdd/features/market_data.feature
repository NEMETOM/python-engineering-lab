Feature: Market data cache behaviour

  Scenario: initial snapshot has all none values
    Given a fresh market cache
    Then last trade price is absent
    And best bid is absent
    And best ask is absent

  Scenario Outline: trade updates last price
    Given a fresh market cache
    When trade price <price> is received
    Then last trade price is <price>

    Examples:
      | price |
      | 100   |
      | 0     |
      | 99.99 |
      | 0.001 |

  Scenario Outline: second trade overwrites first trade price
    Given a fresh market cache
    When trade price <first_price> is received
    And trade price <second_price> is received
    Then last trade price is <second_price>

    Examples:
      | first_price | second_price |
      | 50.00       | 75.00        |
      | 100.00      | 25.00        |

  Scenario Outline: order book update stores best bid and ask
    Given a fresh market cache
    When order book update with bid <bid> and ask <ask> is received
    Then best bid is <bid>
    And best ask is <ask>

    Examples:
      | bid   | ask    |
      | 99.50 | 100.50 |
      | 50.00 | 50.10  |

  Scenario Outline: second order book update overwrites first
    Given a fresh market cache
    When order book update with bid <first_bid> and ask <first_ask> is received
    And order book update with bid <second_bid> and ask <second_ask> is received
    Then best bid is <second_bid>
    And best ask is <second_ask>

    Examples:
      | first_bid | first_ask | second_bid | second_ask |
      | 90.00     | 91.00     | 92.00      | 93.00      |
      | 10.00     | 11.00     | 20.00      | 21.00      |

  Scenario Outline: mid price is computed from best bid and ask
    Given a fresh market cache
    When order book update with bid <bid> and ask <ask> is received
    Then mid price is <mid>

    Examples:
      | bid    | ask    | mid    |
      | 100.00 | 102.00 | 101.00 |
      | 50.00  | 60.00  | 55.00  |

  Scenario Outline: full snapshot reflects trade and order book together
    Given a fresh market cache
    When trade price <price> is received
    And order book update with bid <bid> and ask <ask> is received
    Then last trade price is <price>
    And best bid is <bid>
    And best ask is <ask>

    Examples:
      | price  | bid    | ask    |
      | 150.00 | 149.50 | 150.50 |
      | 75.00  | 74.00  | 76.00  |

  Scenario Outline: mid price is absent before any order book update
    Given a fresh market cache
    When trade price <price> is received
    Then mid price is absent

    Examples:
      | price  |
      | 100.00 |
      | 50.00  |

  Scenario Outline: publisher exposes the cache snapshot
    Given a fresh market cache
    When trade price <price> is received
    And order book update with bid <bid> and ask <ask> is received
    And the publisher publishes
    Then the published snapshot contains last trade price <price>
    And the published snapshot contains best bid <bid>
    And the published snapshot contains best ask <ask>

    Examples:
      | price  | bid    | ask    |
      | 200.00 | 199.00 | 201.00 |
      | 50.00  | 49.00  | 51.00  |
