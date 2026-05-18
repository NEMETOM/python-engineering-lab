Feature: Order Matching
  The matching engine pairs buy and sell orders when their prices cross.
  Trades execute at the resting order's price (price-time priority).

  Background:
    Given an empty order book and matching engine

  Scenario Outline: Buy order matches a resting sell order
    Given a resting SELL order "<sell_id>" at price <ask_price> for quantity <ask_qty>
    When I submit a BUY order "<buy_id>" at price <bid_price> for quantity <bid_qty>
    Then <trade_count> trade(s) are produced
    And the executed trade quantity is <trade_qty>
    And the executed trade price is <trade_price>

    Examples:
      | sell_id | ask_price | ask_qty | buy_id | bid_price | bid_qty | trade_count | trade_qty | trade_price |
      | S1      | 100.0     | 10      | B1     | 100.0     | 10      | 1           | 10        | 100.0       |
      | S1      | 95.0      | 10      | B1     | 100.0     | 10      | 1           | 10        | 95.0        |
      | S1      | 100.0     | 5       | B1     | 100.0     | 10      | 1           | 5         | 100.0       |

  Scenario Outline: Sell order matches a resting buy order
    Given a resting BUY order "<buy_id>" at price <bid_price> for quantity <bid_qty>
    When I submit a SELL order "<sell_id>" at price <ask_price> for quantity <ask_qty>
    Then <trade_count> trade(s) are produced
    And the executed trade quantity is <trade_qty>
    And the executed trade price is <trade_price>

    Examples:
      | buy_id | bid_price | bid_qty | sell_id | ask_price | ask_qty | trade_count | trade_qty | trade_price |
      | B1     | 100.0     | 10      | S1      | 100.0     | 10      | 1           | 10        | 100.0       |
      | B1     | 100.0     | 10      | S1      | 95.0      | 10      | 1           | 10        | 100.0       |
      | B1     | 100.0     | 5       | S1      | 100.0     | 10      | 1           | 5         | 100.0       |

  Scenario Outline: No match when prices do not cross
    Given a resting <counter_side> order "C1" at price <counter_price> for quantity 10
    When I submit a <incoming_side> order "O1" at price <incoming_price> for quantity 10
    Then 0 trade(s) are produced
    And the incoming order rests in the book

    Examples:
      | counter_side | counter_price | incoming_side | incoming_price |
      | SELL         | 105.0         | BUY           | 100.0          |
      | BUY          | 95.0          | SELL          | 100.0          |

  Scenario Outline: Order with no counterpart is added to the book
    When I submit a <side> order "O1" at price <price> for quantity <quantity>
    Then 0 trade(s) are produced
    And the incoming order rests in the book

    Examples:
      | side | price | quantity |
      | BUY  | 100.0 | 10       |
      | SELL | 105.0 | 5        |

  Scenario Outline: Partial fill leaves the remainder resting in the book
    Given a resting <counter_side> order "C1" at price <price> for quantity <counter_qty>
    When I submit a <incoming_side> order "O1" at price <price> for quantity <incoming_qty>
    Then 1 trade(s) are produced
    And the executed trade quantity is <trade_qty>
    And the incoming order rests in the book with quantity <remainder>

    Examples:
      | counter_side | price | counter_qty | incoming_side | incoming_qty | trade_qty | remainder |
      | SELL         | 100.0 | 5           | BUY           | 10           | 5         | 5         |
      | BUY          | 100.0 | 5           | SELL          | 10           | 5         | 5         |

  Scenario Outline: Buy order matches multiple resting sell orders
    Given a resting SELL order "S1" at price <ask_1> for quantity <qty_1>
    And a resting SELL order "S2" at price <ask_2> for quantity <qty_2>
    When I submit a BUY order "B1" at price <bid_price> for quantity <bid_qty>
    Then <trade_count> trade(s) are produced

    Examples:
      | ask_1 | qty_1 | ask_2 | qty_2 | bid_price | bid_qty | trade_count |
      | 99.0  | 5     | 100.0 | 5     | 100.0     | 10      | 2           |
      | 98.0  | 3     | 100.0 | 3     | 100.0     | 10      | 2           |

  Scenario Outline: Sell order matches multiple resting buy orders
    Given a resting BUY order "B1" at price <bid_1> for quantity <qty_1>
    And a resting BUY order "B2" at price <bid_2> for quantity <qty_2>
    When I submit a SELL order "S1" at price <ask_price> for quantity <ask_qty>
    Then <trade_count> trade(s) are produced

    Examples:
      | bid_1 | qty_1 | bid_2 | qty_2 | ask_price | ask_qty | trade_count |
      | 100.0 | 5     | 99.0  | 5     | 99.0      | 10      | 2           |
      | 100.0 | 3     | 99.0  | 3     | 99.0      | 10      | 2           |
