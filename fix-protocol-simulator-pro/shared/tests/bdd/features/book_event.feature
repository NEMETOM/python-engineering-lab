Feature: BookEvent Schema
  BookEvent requires only a symbol; all price fields are optional
  and default to None.

  Scenario Outline: BookEvent with only symbol is valid
    Given a book event with symbol "<symbol>"
    Then the book event is valid
    And best_bid is absent
    And best_ask is absent

    Examples:
      | symbol |
      | AAPL   |
      | BTCUSD |

  Scenario Outline: BookEvent accepts optional bid and ask prices
    Given a book event with symbol "AAPL", best_bid <bid> and best_ask <ask>
    Then the book event is valid
    And best_bid is <bid>
    And best_ask is <ask>

    Examples:
      | bid   | ask   |
      | 99.5  | 100.0 |
      | 149.9 | 150.1 |

  Scenario Outline: All optional price fields can be set
    Given a book event with symbol "AAPL", mid_price <mid> and last_trade_price <last>
    Then the book event is valid
    And mid_price is <mid>
    And last_trade_price is <last>

    Examples:
      | mid   | last  |
      | 99.75 | 99.8  |
      | 150.0 | 149.95 |

  Scenario: Symbol is required
    Given a book event with no symbol
    Then the book event is invalid
