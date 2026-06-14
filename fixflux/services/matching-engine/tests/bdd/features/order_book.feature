Feature: Order Book Management
  The order book tracks outstanding buy and sell orders,
  prioritising the highest bid and the lowest ask.

  Scenario Outline: Best bid reflects the highest buy price
    Given an empty order book
    When I add a BUY order "B1" at price <price_1> for quantity 10
    And I add a BUY order "B2" at price <price_2> for quantity 10
    Then the best bid price is <expected_best_bid>

    Examples:
      | price_1 | price_2 | expected_best_bid |
      | 100.0   | 90.0    | 100.0             |
      | 85.0    | 95.0    | 95.0              |

  Scenario Outline: Best ask reflects the lowest sell price
    Given an empty order book
    When I add a SELL order "S1" at price <price_1> for quantity 10
    And I add a SELL order "S2" at price <price_2> for quantity 10
    Then the best ask price is <expected_best_ask>

    Examples:
      | price_1 | price_2 | expected_best_ask |
      | 110.0   | 105.0   | 105.0             |
      | 100.0   | 115.0   | 100.0             |

  Scenario Outline: Empty book has no best price on either side
    Given an empty order book
    Then the best <side> price is absent

    Examples:
      | side |
      | bid  |
      | ask  |

  Scenario Outline: Orders on one side do not populate the opposite side
    Given an empty order book
    When I add a <added_side> order "O1" at price 100.0 for quantity 10
    Then the best <absent_side> price is absent

    Examples:
      | added_side | absent_side |
      | BUY        | ask         |
      | SELL       | bid         |
