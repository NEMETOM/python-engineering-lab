@integration @e2e @needs_kafka @needs_compliance_api
Feature: Compliance Rules & Audit Trail Pipeline
  Compliance-service never blocks an order - it passively taps raw_orders
  (compliance rules) and validated_orders (surveillance rules), scores every
  violation it finds, and leaves an audit trail entry for every single order
  it sees, violating or not.

  Requires: Kafka/Redpanda + compliance-consumer + compliance-api running.
  Start with: docker compose --profile full up

  Note: MarketHoursRule is deliberately not exercised here - it compares the
  real wall clock against a configured trading window with no way to inject
  a fake "as of" time, so it cannot be triggered on demand. It's demonstrated
  via code walkthrough only (see compliance_policies.yaml), not a live test.

  # ── PriceDeviationRule: price far from the symbol's rolling average ────────

  Scenario Outline: An order priced far from the rolling average triggers a PriceDeviationRule violation
    Given a unique compliance test client is created
    And a price baseline of <baseline_price> has been established for symbol "<symbol>" on raw_orders
    When an order for the test client symbol "<symbol>" price <deviant_price> qty 10 is published to raw_orders
    Then a compliance violation for rule "PriceDeviationRule" for the test client appears within 15 seconds

    Examples:
      | symbol       | baseline_price | deviant_price |
      | COMPPRICE1   | 100.00          | 130.00        |
      | COMPPRICE2   | 50.00           | 65.00         |

  # ── RapidFireRule: too many orders too fast ─────────────────────────────────

  Scenario Outline: A client submitting an order burst triggers a RapidFireRule violation
    Given a unique compliance test client is created
    When 11 orders for the test client symbol "<symbol>" are rapidly published to validated_orders
    Then a compliance violation for rule "RapidFireRule" for the test client appears within 15 seconds

    Examples:
      | symbol      |
      | COMPBURST1  |
      | COMPBURST2  |

  # ── VolumeSpikeRule: one order far above the symbol's baseline size ────────

  Scenario Outline: An order far exceeding the volume baseline triggers a VolumeSpikeRule violation
    Given a unique compliance test client is created
    And a volume baseline of qty <baseline_qty> has been established for symbol "<symbol>" on validated_orders
    When an order for the test client symbol "<symbol>" qty <spike_qty> is published to validated_orders
    Then a compliance violation for rule "VolumeSpikeRule" for the test client appears within 15 seconds

    Examples:
      | symbol      | baseline_qty | spike_qty |
      | COMPSPIKE1  | 100          | 1000      |
      | COMPSPIKE2  | 50           | 600       |

  # ── RepeatedOrdersRule: the identical order, submitted too many times ──────

  Scenario Outline: Submitting an identical order repeatedly triggers a RepeatedOrdersRule violation
    Given a unique compliance test client is created
    When an identical order for the test client symbol "<symbol>" side "BUY" price <price> qty <qty> is published to validated_orders 5 times
    Then a compliance violation for rule "RepeatedOrdersRule" for the test client appears within 15 seconds

    Examples:
      | symbol      | price  | qty |
      | COMPREPEAT1 | 75.00  | 20  |
      | COMPREPEAT2 | 200.00 | 5   |

  # ── Risk scoring: repeated violations flag a client as high-risk ───────────

  Scenario Outline: Two wash-trading violations push a client's cumulative risk score past the high-risk threshold
    Given a unique compliance test client is created
    When the test client wash-trades symbol "<symbol_a>" via validated_orders
    And the test client wash-trades symbol "<symbol_b>" via validated_orders
    Then the test client is flagged high-risk in GET /risk within 15 seconds

    Examples:
      | symbol_a    | symbol_b    |
      | COMPRISK1A  | COMPRISK1B  |
      | COMPRISK2A  | COMPRISK2B  |

  # ── Audit trail: every order leaves a footprint, violating or not ──────────

  Scenario Outline: Every order leaves an order_received audit entry, and a violating order also leaves a violation_detected entry
    Given a unique compliance test client is created
    When a clean order for the test client symbol "<clean_symbol>" price 100.00 qty 10 is published to raw_orders
    And an order for the test client symbol "<dup_symbol>" price 50.00 qty 5 is published to raw_orders twice
    Then the "order_received" audit entry for the test client appears within 15 seconds
    And the "violation_detected" audit entry for the test client appears within 15 seconds

    Examples:
      | clean_symbol | dup_symbol   |
      | COMPAUDIT1A  | COMPAUDIT1B  |
      | COMPAUDIT2A  | COMPAUDIT2B  |
