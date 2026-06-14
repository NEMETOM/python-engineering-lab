Feature: OrderEvent Schema
  OrderEvent validates side (BUY/SELL), positive price, positive quantity,
  and requires all core fields.

  Scenario Outline: Valid order events with both sides are accepted
    Given an order event with side "<side>", price <price>, quantity <quantity>
    Then the order event is valid
    And the order event side is "<side>"

    Examples:
      | side | price | quantity |
      | BUY  | 100.0 | 10       |
      | SELL | 50.5  | 5        |

  Scenario Outline: Invalid side values are rejected
    Given an order event with side "<side>", price 100.0, quantity 10
    Then the order event is invalid

    Examples:
      | side |
      | HOLD |
      | buy  |

  Scenario Outline: Non-positive price is rejected
    Given an order event with side "BUY", price <price>, quantity 10
    Then the order event is invalid

    Examples:
      | price |
      | 0.0   |
      | -1.0  |

  Scenario Outline: Non-positive quantity is rejected
    Given an order event with side "BUY", price 100.0, quantity <quantity>
    Then the order event is invalid

    Examples:
      | quantity |
      | 0        |
      | -5       |

  Scenario Outline: Missing required fields are rejected
    Given an order event is missing the "<field>" field
    Then the order event is invalid

    Examples:
      | field    |
      | order_id |
      | symbol   |
      | side     |
      | price    |
      | quantity |
