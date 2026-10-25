Feature: MiFID II post-trade regulatory reporting
  reporting-service turns every trade into one regulatory record, enriched from
  reference data with LEIs, trading capacity and CFI code. Trades in scope with
  complete reference data are REPORTABLE; out-of-scope instruments are
  NOT_REPORTABLE; missing reference data is flagged INCOMPLETE, never defaulted.
  RTS 1 Art. 14(1)(a) requires publication within one minute of execution.

  Scenario Outline: In-scope trades between known participants are reportable
    Given a trade in "<symbol>" between "<buyer>" and "<seller>" executed 1 seconds ago
    When the trade is reported
    Then the report status is "REPORTABLE"
    And the report carries valid LEIs for both parties
    And the report has CFI code "<cfi>" and trading capacity "DEAL" for both sides

    Examples:
      | symbol | buyer       | seller       | cfi    |
      | AAPL   | DEMO_BUYER1 | DEMO_SELLER1 | ESVUFR |
      | MSFT   | TRADER1     | TRADER2      | ESVUFR |

  Scenario Outline: Out-of-scope instruments are recorded but not reportable
    Given a trade in "<symbol>" between "DEMO_BUYER1" and "DEMO_SELLER1" executed 1 seconds ago
    When the trade is reported
    Then the report status is "NOT_REPORTABLE"
    And the status reason mentions "<reason>"

    Examples:
      | symbol | reason        |
      | EURUSD | FX spot       |
      | GBPUSD | FX spot       |
      | BTCUSD | crypto-assets |
      | ETHUSD | crypto-assets |

  Scenario Outline: Missing reference data is flagged as incomplete
    Given a trade in "<symbol>" between "<buyer>" and "<seller>" executed 1 seconds ago
    When the trade is reported
    Then the report status is "INCOMPLETE"
    And the status reason mentions "<reason>"

    Examples:
      | symbol  | buyer       | seller       | reason                              |
      | AAPL    | VOL_B0001   | DEMO_SELLER1 | no LEI for buyer VOL_B0001          |
      | MSFT    | DEMO_BUYER1 | VOL_S0042    | no LEI for seller VOL_S0042         |
      | DOGEUSD | DEMO_BUYER1 | DEMO_SELLER1 | no reference data for instrument    |

  Scenario Outline: Reports later than one minute after execution are flagged
    Given a trade in "AAPL" between "DEMO_BUYER1" and "DEMO_SELLER1" executed <seconds> seconds ago
    When the trade is reported
    Then the report status is "REPORTABLE"
    And the publication deadline breached flag is "<breached>"

    Examples:
      | seconds | breached |
      | 1       | false    |
      | 59      | false    |
      | 61      | true     |
      | 600     | true     |

  Scenario Outline: Trades replayed by fix-replay resolve to the original participants
    Given a trade in "AAPL" between "<buyer>" and "<seller>" executed 1 seconds ago
    When the trade is reported
    Then the report status is "REPORTABLE"
    And the report keeps buyer client ID "<buyer>"

    Examples:
      | buyer                    | seller                    |
      | RPL-ab12cd34-DEMO_BUYER1 | RPL-ab12cd34-DEMO_SELLER1 |
      | RPL-0000ffff-TRADER1     | RPL-0000ffff-TRADER2      |

  Scenario Outline: A redelivered trade produces exactly one report
    Given a trade in "<symbol>" between "DEMO_BUYER1" and "DEMO_SELLER1" executed 1 seconds ago
    When the same trade message is consumed <times> times
    Then exactly 1 report is stored for the trade
    And <duplicates> deliveries are counted as duplicates

    Examples:
      | symbol | times | duplicates |
      | AAPL   | 2     | 1          |
      | EURUSD | 3     | 2          |
