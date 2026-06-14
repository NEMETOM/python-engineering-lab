Feature: Shared Exceptions
  The shared exception hierarchy provides AppException as a base,
  with ValidationError and InfrastructureError as typed sub-classes.

  Scenario Outline: AppException stores the error message
    Given an AppException is raised with message "<message>"
    Then the exception message is "<message>"
    And it is an instance of Exception

    Examples:
      | message                  |
      | validation failed        |
      | connection refused       |

  Scenario Outline: ValidationError inherits from AppException
    Given a ValidationError is raised with message "<message>"
    Then the exception is an instance of AppException
    And the exception message is "<message>"

    Examples:
      | message                  |
      | price must be positive   |
      | side must be BUY or SELL |

  Scenario Outline: InfrastructureError inherits from AppException
    Given an InfrastructureError is raised with message "<message>"
    Then the exception is an instance of AppException
    And the exception message is "<message>"

    Examples:
      | message                  |
      | kafka connection failed  |
      | database unavailable     |

  Scenario Outline: Typed exceptions can be caught as AppException
    Given a <exception_type> is raised with message "some error"
    Then catching AppException succeeds

    Examples:
      | exception_type     |
      | ValidationError    |
      | InfrastructureError |
