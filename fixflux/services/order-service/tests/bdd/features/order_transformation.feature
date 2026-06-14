Feature: Order Transformation
  The transformer promotes a raw order event into a validated order event,
  assigning a unique UUID order ID and preserving all original fields unchanged.

  Scenario Outline: All fields are carried through to the validated order
    Given a raw order with symbol "<symbol>", side "<side>", price <price>, quantity <quantity>
    When the transformer processes the order
    Then the validated order has symbol "<symbol>"
    And the validated order has side "<side>"
    And the validated order has price <price>
    And the validated order has quantity <quantity>

    Examples:
      | symbol | side | price  | quantity |
      | AAPL   | BUY  | 100.0  | 10       |
      | TSLA   | SELL | 250.5  | 5        |
      | MSFT   | BUY  | 380.0  | 20       |

  Scenario Outline: Each transformation assigns a valid UUID as the order ID
    Given a raw order with symbol "<symbol>", side "<side>", price <price>, quantity <quantity>
    When the transformer processes the order
    Then the validated order ID is a valid UUID

    Examples:
      | symbol | side | price  | quantity |
      | AAPL   | BUY  | 100.0  | 10       |
      | TSLA   | SELL | 250.5  | 5        |

  Scenario: Repeated transformations of the same raw order yield unique order IDs
    Given a raw order with symbol "AAPL", side "BUY", price 100.0, quantity 10
    When the transformer processes the order twice
    Then the two order IDs are different
