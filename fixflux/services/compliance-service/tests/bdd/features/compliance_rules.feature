Feature: Compliance Rules Engine
  The compliance rules engine evaluates each incoming order against configurable
  policy rules and raises violations with the correct severity when thresholds are breached.

  Scenario Outline: Missing client ID is flagged as a HIGH violation
    Given a compliance rules engine with default policies
    When an order arrives with client_id "<client_id>", symbol "<symbol>", quantity <qty>, price <price>
    Then the rule "<rule>" is "<outcome>" with severity "<severity>"

    Examples:
      | client_id | symbol | qty | price | rule                | outcome   | severity |
      |           | EURUSD | 100 | 1.09  | MissingClientIdRule | triggered | HIGH     |
      | CLIENT1   | EURUSD | 100 | 1.09  | MissingClientIdRule | not fired |          |

  Scenario Outline: Excessive trade size is flagged as a HIGH violation
    Given a trade size rule with default limit <limit>
    When an order for symbol "<symbol>" with quantity <qty> is evaluated
    Then the trade size violation is "<outcome>"

    Examples:
      | symbol | qty    | limit | outcome   |
      | EURUSD | 9999   | 10000 | not fired |
      | EURUSD | 10001  | 10000 | triggered |
      | BTCUSD | 99     | 100   | not fired |
      | BTCUSD | 101    | 100   | triggered |

  Scenario Outline: Invalid symbol is flagged as a CRITICAL violation
    Given a symbol rule allowing only "EURUSD,BTCUSD"
    When an order for symbol "<symbol>" is evaluated
    Then the invalid symbol violation is "<outcome>"

    Examples:
      | symbol  | outcome   |
      | EURUSD  | not fired |
      | BTCUSD  | not fired |
      | XYZABC  | triggered |
      | DOGEUSD | triggered |

  Scenario Outline: Duplicate orders within the time window are flagged
    Given a duplicate order rule with a 60-second window
    When the same order is submitted <times> times
    Then the duplicate violation fires on the "<fire_on>" submission

    Examples:
      | times | fire_on |
      | 2     | second  |
      | 3     | second  |
