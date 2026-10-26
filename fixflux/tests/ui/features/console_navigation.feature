Feature: FixFlux Console navigation
  The Console's three tabs share one header. Each tab opens its own page and
  is the only tab marked as the current page.

  Scenario Outline: Each tab opens its page and is the active tab
    Given I open the FixFlux Console at "<start_path>"
    When I click the "<tab>" tab
    Then the "<tab>" tab is the active tab
    And the page heading reads "<heading>"

    Examples:
      | start_path   | tab              | heading                         |
      | /            | Compliance Rules | Compliance & Surveillance Rules |
      | /            | Market Data      | Live Market Data                |
      | /market-data | Fix Msg Injector | FIX Message Test Injector       |
