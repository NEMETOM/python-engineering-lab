Feature: Fix Msg Injector
  Raw FIX New Order Single lines pasted into the injector are parsed and
  published to the raw_orders topic, and the page reports the outcome.

  Scenario Outline: Valid FIX orders are published
    Given the Fix Msg Injector page is open
    When I paste <count> valid New Order Single lines for "<symbol>" and submit
    Then the injector status reads "<count>/<count> published, 0 rejected."
    And <count> results are marked as published
    And <count> orders for "<symbol>" were sent to raw_orders

    Examples:
      | count | symbol |
      | 1     | AAPL   |
      | 3     | EURUSD |
