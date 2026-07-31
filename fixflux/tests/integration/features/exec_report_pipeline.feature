@integration @needs_kafka @needs_risk_service @needs_exec_reports @needs_full_stack
Feature: FIX Execution Report Pipeline (35=8)
  Every state transition an order goes through - accepted, rejected, or filled -
  must produce a FIX Execution Report (MsgType 35=8) on the execution_reports
  topic. This is the audit-grade event a MiFIR transaction-reporting pipeline
  would consume directly, so each transition is exercised end-to-end here
  rather than only at the unit level.

  Requires: Kafka/Redpanda + risk-service + matching-engine running.
  Start with: docker compose --profile full up

  # ── New: risk-service acknowledges an approved order ──────────────────────

  Scenario Outline: An approved order emits a New execution report
    Given a unique risk test client is created
    And a validated order for the test client symbol "<symbol>" side "BUY" price <price> qty <qty>
    When the order is published to validated_orders
    Then an execution report for the order with ExecType "0" appears within 10 seconds
    And the execution report OrdStatus is "0"

    Examples:
      | symbol   | price  | qty |
      | EXECNEW1 | 100.00 | 10  |
      | EXECNEW2 | 50.00  | 20  |

  # ── Rejected: risk-service blocks an order before it reaches the market ───

  Scenario Outline: A rejected order emits a Rejected execution report carrying the rejection reason
    Given a unique risk test client is created
    And a validated order for the test client symbol "<symbol>" side "BUY" price <price> qty <qty>
    When the order is published to validated_orders
    Then an execution report for the order with ExecType "8" appears within 10 seconds
    And the execution report OrdStatus is "8"
    And the execution report reason contains "<reason_fragment>"

    Examples:
      | symbol      | price    | qty  | reason_fragment |
      | BTCUSD      | 50000.00 | 25   | notional        |
      | EXECREJECT1 | 175.00   | 6000 | notional        |

  # ── Fill: a matched trade emits one Fill report per side ───────────────────

  Scenario Outline: A matched trade emits a Fill execution report for both sides with the correct client ID
    Given a unique risk test client is created
    And a second unique risk test client is created
    And a crossing buy order for the test client symbol "<symbol>" at price <price> qty <qty>
    And a crossing sell order for the second test client symbol "<symbol>" at price <price> qty <qty>
    When both crossing orders are published to validated_orders
    Then a Fill execution report for the buy order appears within 15 seconds
    And a Fill execution report for the sell order appears within 15 seconds
    And the buy Fill execution report has client_id matching the test client
    And the sell Fill execution report has client_id matching the second test client

    Examples:
      | symbol   | price  | qty |
      | EXECFIL1 | 250.00 | 15  |
      | EXECFIL2 | 60.00  | 8   |
