Feature: Price calculations

  Scenario Outline: Apply discount correctly
    Given the original price is <price>
    When I apply a discount of <discount> percent
    Then the final price should be <expected>

    Examples:
      | price | discount | expected |
      | 100   | 10       | 90       |
      | 200   | 50       | 100      |
      | 50    | 0        | 50       |

  Scenario Outline: Add VAT correctly
    Given the original price is <price>
    When I add VAT of <vat> percent
    Then the final price should be <expected>

    Examples:
      | price | vat | expected |
      | 100   | 20  | 120      |
      | 50    | 10  | 55       |

  Scenario: Reject negative price
    Given the original price is -10
    When I apply a discount of 10 percent
    Then a ValueError should be raised

  Scenario: Reject invalid discount
    Given the original price is 100
    When I apply a discount of 150 percent
    Then a ValueError should be raised
