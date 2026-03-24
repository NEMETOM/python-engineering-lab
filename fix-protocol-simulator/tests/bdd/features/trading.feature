Feature: Trading via FIX protocol

  Scenario: Match buy and sell orders
    Given the order book is empty
    When a BUY order is placed at price 100 for quantity 10
    And a SELL order is placed at price 100 for quantity 10
    Then a trade should be executed
    And the trade price should be 100
    And the trade quantity should be 10

  Scenario: No match when prices don't cross
    Given the order book is empty
    When a BUY order is placed at price 90 for quantity 10
    And a SELL order is placed at price 100 for quantity 10
    Then no trade should be executed

  Scenario: Partial fill uses minimum quantity
    Given the order book is empty
    When a BUY order is placed at price 100 for quantity 3
    And a SELL order is placed at price 100 for quantity 10
    Then a trade should be executed
    And the trade quantity should be 3

  Scenario: SELL matches the best BID when multiple buy orders exist
    Given the order book is empty
    And the following BUY orders are in the book:
      | order_id | price | quantity |
      | 1        | 95    | 5        |
      | 2        | 105   | 5        |
    When a SELL order is placed at price 95 for quantity 5
    Then a trade should be executed
    And the trade price should be 105

  Scenario Outline: Trade executes at correct price and quantity
    Given the order book is empty
    When a BUY order is placed at price <buy_price> for quantity <buy_qty>
    And a SELL order is placed at price <sell_price> for quantity <sell_qty>
    Then the trade result should be <outcome>

    Examples:
      | buy_price | buy_qty | sell_price | sell_qty | outcome    |
      | 100       | 10      | 100        | 10       | executed   |
      | 100       | 10      | 90         | 10       | executed   |
      | 90        | 10      | 100        | 10       | no_trade   |
      | 100       | 5       | 100        | 10       | executed   |
