Feature: Time Utilities
  utc_now() returns a timezone-aware UTC datetime;
  to_iso() converts a datetime to its ISO 8601 string representation.

  Scenario: utc_now returns a timezone-aware UTC datetime
    When utc_now is called
    Then the result is a datetime instance
    And the result is timezone-aware
    And the result timezone is UTC

  Scenario Outline: to_iso converts a UTC datetime to an ISO string
    Given the UTC datetime "<input>"
    When to_iso is called with that datetime
    Then the ISO result is "<input>"

    Examples:
      | input                     |
      | 2024-01-15T10:30:00+00:00 |
      | 2024-06-01T12:00:00+00:00 |

  Scenario Outline: to_iso result is parseable back to the original datetime
    Given the UTC datetime "<input>"
    When to_iso is called with that datetime
    Then parsing the ISO result yields the original datetime

    Examples:
      | input                     |
      | 2024-03-20T08:00:00+00:00 |
      | 2024-12-31T23:59:00+00:00 |
