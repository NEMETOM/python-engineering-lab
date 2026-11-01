Feature: Replay FIX files through the pipeline and capture execution reports
  fix-replay parses FIX order files, publishes each valid order to raw_orders
  under a run-namespaced client_id, collects that run's execution reports and
  writes a JSON report, optionally diffed against a baseline. Kafka and
  matching-engine's /metrics are faked; the parser, preflight, replayer,
  collector and report code run for real.

  Scenario Outline: A dry run validates the file without touching Kafka
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And the file "<file>" also contains <session> session messages
    When I replay "<file>" as a dry run
    Then the replay exits with "ok"
    And no orders were published to raw_orders
    And no execution_reports consumer was opened

    Examples:
      | file     | buys | sells | symbol | price  | qty  | session |
      | demo.txt | 1    | 1     | AAPL   | 175.5  | 100  | 1       |
      | fx.txt   | 3    | 2     | EURUSD | 1.0901 | 1000 | 2       |

  Scenario Outline: Crossing orders are replayed under a namespaced client and fill
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And the pipeline accepts every order
    When I replay "<file>" with run id "<run_id>"
    Then the replay exits with "ok"
    And <sent> orders were published to raw_orders
    And every published client_id starts with "RPL-<run_id>-"
    And the report summary shows <sent> sent, <new> new, <rejected> rejected and <fills> fills
    And the report's filled quantity is <filled_qty>
    And the execution_reports consumer was closed

    Examples:
      | file       | buys | sells | symbol | price   | qty | run_id | sent | new | rejected | fills | filled_qty |
      | demo.txt   | 1    | 1     | AAPL   | 175.5   | 100 | r1     | 2    | 2   | 0        | 2     | 200        |
      | msft.txt   | 2    | 2     | MSFT   | 414.9   | 50  | r2     | 4    | 4   | 0        | 4     | 200        |
      | crypto.txt | 2    | 1     | BTCUSD | 50010.0 | 2   | r3     | 3    | 3   | 0        | 2     | 4          |

  Scenario Outline: Session messages are skipped and invalid lines are reported but never sent
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And the file "<file>" also contains <session> session messages
    And the file "<file>" also contains a "<kind>" invalid line
    And the pipeline accepts every order
    When I replay "<file>" with run id "<run_id>"
    Then the replay exits with "ok"
    And <sent> orders were published to raw_orders
    And the report shows <session> session messages skipped and 1 invalid line
    And the report lists an invalid line with an error containing "<error>"

    Examples:
      | file    | buys | sells | symbol | price | qty | session | kind                 | run_id | sent | error                              |
      | a.txt   | 1    | 1     | AAPL   | 175.5 | 100 | 1       | missing-symbol       | i1     | 2    | missing required tag(s): 55        |
      | b.txt   | 1    | 0     | MSFT   | 414.9 | 10  | 2       | unknown-side         | i2     | 1    | unknown side 54='3'                |
      | c.txt   | 2    | 2     | TSLA   | 250.0 | 5   | 0       | zero-price           | i3     | 4    | price and quantity must be positive |
      | d.txt   | 1    | 1     | AAPL   | 175.5 | 100 | 1       | non-numeric-quantity | i4     | 2    | non-numeric price/quantity         |
      | e.txt   | 0    | 1     | NVDA   | 120.0 | 30  | 3       | unsupported-type     | i5     | 1    | unsupported message type 35='G'    |

  Scenario Outline: Replaying a file again on a reset pipeline matches its baseline
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And the pipeline accepts every order
    And a baseline was recorded by replaying "<file>" with run id "<base_run>"
    When I replay "<file>" with run id "<run_id>" against that baseline
    Then the replay exits with "ok"
    And the baseline diff is empty

    Examples:
      | file     | buys | sells | symbol | price | qty | base_run | run_id |
      | demo.txt | 1    | 1     | AAPL   | 175.5 | 100 | b1       | c1     |
      | gbp.txt  | 3    | 2     | GBPUSD | 1.27  | 500 | b2       | c2     |

  Scenario Outline: Resting orders don't block a replay when explicitly allowed
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And matching-engine already has <resting> resting orders on "<symbol>"
    And the pipeline accepts every order
    When I replay "<file>" with run id "<run_id>" and options "--allow-resting"
    Then the replay exits with "ok"
    And <sent> orders were published to raw_orders

    Examples:
      | file     | buys | sells | symbol | price | qty | resting | run_id | sent |
      | demo.txt | 1    | 1     | AAPL   | 175.5 | 100 | 1       | a1     | 2    |
      | msft.txt | 2    | 1     | MSFT   | 414.9 | 50  | 7       | a2     | 3    |

  Scenario Outline: An unreachable /metrics endpoint skips the resting-order check
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And matching-engine's /metrics endpoint is unreachable
    And the pipeline accepts every order
    When I replay "<file>" with run id "<run_id>"
    Then the replay exits with "ok"
    And <sent> orders were published to raw_orders

    Examples:
      | file     | buys | sells | symbol | price | qty | run_id | sent |
      | demo.txt | 1    | 1     | AAPL   | 175.5 | 100 | u1     | 2    |
      | eur.txt  | 1    | 2     | EURUSD | 1.09  | 900 | u2     | 3    |

  @negative
  Scenario Outline: Orders rejected by risk-service are counted with their reason
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And risk-service rejects orders for "<symbol>" with reason "<reason>"
    When I replay "<file>" with run id "<run_id>"
    Then the replay exits with "ok"
    And the report summary shows <sent> sent, 0 new, <sent> rejected and 0 fills
    And the report counts <sent> rejections with reason "<reason>"

    Examples:
      | file     | buys | sells | symbol | price | qty     | run_id | sent | reason                      |
      | big.txt  | 1    | 1     | AAPL   | 175.5 | 1000000 | x1     | 2    | MAX_ORDER_QTY exceeded      |
      | fat.txt  | 2    | 1     | MSFT   | 999.0 | 10      | x2     | 3    | fat finger: price deviation |

  @negative
  Scenario Outline: A pipeline that never acknowledges orders ends the run as incomplete
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And the pipeline never acknowledges orders
    When I replay "<file>" with run id "<run_id>" and options "--timeout <timeout>"
    Then the replay exits with "incomplete"
    And <sent> orders were published to raw_orders
    And the report shows 0 acks received and the run timed out

    Examples:
      | file     | buys | sells | symbol | price | qty | run_id | timeout | sent |
      | demo.txt | 1    | 1     | AAPL   | 175.5 | 100 | t1     | 0.1     | 2    |
      | eur.txt  | 2    | 3     | EURUSD | 1.09  | 900 | t2     | 0.2     | 5    |

  @negative
  Scenario Outline: Resting orders on a replayed symbol abort the run before anything is sent
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And matching-engine already has <resting> resting orders on "<symbol>"
    When I replay "<file>" with run id "<run_id>"
    Then the replay exits with "preflight"
    And no orders were published to raw_orders
    And no execution_reports consumer was opened

    Examples:
      | file     | buys | sells | symbol | price | qty | resting | run_id |
      | demo.txt | 1    | 1     | AAPL   | 175.5 | 100 | 1       | p1     |
      | msft.txt | 2    | 2     | MSFT   | 414.9 | 50  | 12      | p2     |

  @negative
  Scenario Outline: Executions that differ from the baseline are reported as a regression
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And the pipeline accepts every order
    And a baseline was recorded by replaying "<file>" with run id "<base_run>"
    And risk-service rejects orders for "<symbol>" with reason "<reason>"
    When I replay "<file>" with run id "<run_id>" against that baseline
    Then the replay exits with "regression"
    And the baseline diff has <missing> missing and <unexpected> unexpected executions

    Examples:
      | file     | buys | sells | symbol | price | qty | base_run | run_id | reason              | missing | unexpected |
      | demo.txt | 1    | 1     | AAPL   | 175.5 | 100 | b1       | g1     | symbol halted       | 4       | 2          |
      | msft.txt | 2    | 2     | MSFT   | 414.9 | 50  | b2       | g2     | max open orders hit | 8       | 4          |

  @negative
  Scenario Outline: A missing execution_reports topic is a setup error, not a regression
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And the execution_reports topic does not exist
    When I replay "<file>" with run id "<run_id>"
    Then the replay exits with "error"
    And no orders were published to raw_orders

    Examples:
      | file     | buys | sells | symbol | price | qty | run_id |
      | demo.txt | 1    | 1     | AAPL   | 175.5 | 100 | m1     |
      | eur.txt  | 2    | 1     | EURUSD | 1.09  | 900 | m2     |

  @negative
  Scenario Outline: A missing input file is a setup error, not a regression
    Given the FIX file "<file>" does not exist
    When I replay "<file>" with run id "<run_id>"
    Then the replay exits with "error"
    And no execution_reports consumer was opened

    Examples:
      | file           | run_id |
      | missing.txt    | e1     |
      | old_orders.fix | e2     |

  @negative
  Scenario Outline: A file with no valid orders is refused instead of passing trivially
    Given a FIX file "<file>" with only a "<kind>" invalid line
    And the file "<file>" also contains <session> session messages
    When I replay "<file>" with run id "<run_id>"
    Then the replay exits with "error"
    And no orders were published to raw_orders
    And no execution_reports consumer was opened

    Examples:
      | file    | kind             | session | run_id |
      | bad.txt | unknown-side     | 2       | v1     |
      | ack.txt | unsupported-type | 0       | v2     |

  @negative
  Scenario Outline: An unreadable baseline fails before any order is sent
    Given a FIX file "<file>" with <buys> buy and <sells> sell orders for "<symbol>" at <price> for <qty>
    And the pipeline accepts every order
    And the baseline "<baseline>" does not exist
    When I replay "<file>" with run id "<run_id>" against that baseline
    Then the replay exits with "error"
    And no orders were published to raw_orders

    Examples:
      | file     | buys | sells | symbol | price | qty | baseline           | run_id |
      | demo.txt | 1    | 1     | AAPL   | 175.5 | 100 | demo.json          | n1     |
      | eur.txt  | 2    | 1     | EURUSD | 1.09  | 900 | all_instruments.json | n2   |
