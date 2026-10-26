Feature: Market Data
  The Market Data tab streams snapshots from market-data-api over a WebSocket
  and shows one row per symbol, formatted to the instrument's price level.

  Scenario Outline: A streamed snapshot appears as a formatted row
    Given the Market Data page is open and the stream is live
    When a snapshot for "<symbol>" with bid <bid> and ask <ask> arrives
    Then the "<symbol>" row shows bid "<bid_text>", ask "<ask_text>" and mid "<mid_text>"
    And the waiting message is hidden
    And the update counter reads "1 update"

    Examples:
      | symbol | bid    | ask    | bid_text | ask_text | mid_text |
      | AAPL   | 174.9  | 175.1  | 174.90   | 175.10   | 175.00   |
      | EURUSD | 1.0899 | 1.0901 | 1.08990  | 1.09010  | 1.09000  |
