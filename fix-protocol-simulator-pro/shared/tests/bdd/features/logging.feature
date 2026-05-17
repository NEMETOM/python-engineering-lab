Feature: Observability - Logging
  get_logger returns named loggers; configure_logging sets up the root
  handler and is idempotent; JsonFormatter produces structured JSON output.

  Scenario Outline: get_logger returns a named logger
    When get_logger is called with name "<name>"
    Then a logger named "<name>" is returned

    Examples:
      | name             |
      | order.service    |
      | matching.engine  |

  Scenario: configure_logging adds a handler to the root logger
    Given the root logger has no handlers
    When configure_logging is called
    Then the root logger has at least one handler

  Scenario: configure_logging is idempotent
    Given the root logger has no handlers
    When configure_logging is called twice
    Then the root logger has exactly one handler

  Scenario Outline: JsonFormatter produces valid JSON with required fields
    Given a log record with level "<level>" and message "<message>"
    When the JsonFormatter formats the record
    Then the output is valid JSON
    And the output field "level" equals "<level>"
    And the output field "message" equals "<message>"

    Examples:
      | level | message          |
      | INFO  | order received   |
      | ERROR | connection failed |
