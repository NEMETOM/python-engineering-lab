# fix-replay

Replays FIX message files through the live FixFlux pipeline and records what came out the other
end (`execution_reports`), for backtesting a scenario or regression-testing a change against a saved
baseline.

## How it works

1. Parses each file (pipe- or SOH-delimited). Session messages (`35=A/0/1/5`) are skipped. Lines
   that order-service would drop are reported as invalid and **not sent**: missing tags,
   non-`35=D`, an unknown side, or non-positive price/quantity. Every order that is sent therefore
   gets exactly one New or Rejected execution report from risk-service.
2. Opens a groupless consumer on `execution_reports`, positioned at the end of the topic
   (`shared.infrastructure.kafka_client.create_tail_consumer`). Because it has no consumer group, it
   doesn't leave a group behind for kafka-exporter to report as lagging.
3. Publishes each order to `raw_orders` in the same shape as the filedrop client, at `--rate`
   orders/second, with `client_id` rewritten to `RPL-<run-id>-<original>`.
4. Collects reports for that prefix until every order is acked and no report has arrived for
   `--settle` seconds, or until `--timeout` expires.
5. Writes a JSON report. With `--baseline`, it diffs the run against a previous report.

**Why the `client_id` is namespaced.** Each run is isolated from the open orders and positions left
by earlier runs (which otherwise trip `RISK_MAX_OPEN_ORDERS`). Each original client's orders still
stay together under one participant, so per-client risk limits and wash-trading detection behave as
they would for the original flow. The run's execution reports are found by that prefix, because
`order_id` is a fresh uuid assigned by order-service and can't be correlated with the input lines.

## Run it

On the droplet, or anywhere the stack is running:

```bash
cd ~/python-engineering-lab/fixflux

# Backtest: replay a scenario, keep the report
docker compose --profile replay run --rm fix-replay \
  /data/demo_matched_orders.txt --out /results/demo.json

# Record a baseline once, from a known-good build on a freshly reset pipeline
docker compose --profile replay run --rm fix-replay \
  /data/matching_trd_all_instruments.txt --out /results/all_instruments.json
cp replay-results/all_instruments.json clients/fix-replay/baselines/

# Regression test after a change: exit code 1 + a diff if executions differ
docker compose --profile replay run --rm fix-replay \
  /data/matching_trd_all_instruments.txt --baseline /baselines/all_instruments.json
```

Locally, without Docker: `pip install -e ./shared -e ./clients/fix-replay`, then
`KAFKA_BROKER=localhost:9092 fix-replay data/demo_matched_orders.txt`. Use `--dry-run` to parse
and validate a file without sending anything.

| Exit code | Meaning                                                             |
|-----------|---------------------------------------------------------------------|
| 0         | Run complete (and matches `--baseline`, if given)                   |
| 1         | Executions differ from `--baseline`; the diff is printed to stdout  |
| 2         | Not every order was acked within `--timeout`                        |
| 3         | Pre-flight refused: resting orders already on a replayed symbol     |

## What the baseline compares

`executions`: one row per execution report with `client_id` (prefix stripped), `exec_type`,
`symbol`, `side`, `price`, `order_qty`, `last_px`, `last_qty` and `reason`. `order_id`, `exec_id`
and timestamps are regenerated on every run and are excluded. Rows are compared as a sorted
multiset, not in arrival order: risk-service and matching-engine produce to `execution_reports`
independently, so the interleaving of New and Fill reports isn't stable between runs.

## Limits: when results are not reproducible

This replays against the **live** pipeline, so it shares global state with any other traffic:

- **Order book.** Replayed orders can match orders that are already resting from other clients.
  The pre-flight reads `orders_in_book` from matching-engine's `/metrics` and refuses to run if a
  replayed symbol already has resting orders (`--allow-resting` overrides this). If `/metrics` is
  unreachable, it logs a warning and continues.
- **Last trade price.** risk-service's fat-finger check compares against the last trade per symbol,
  including trades from outside the replay. It also consumes `trades` and `validated_orders` in
  one loop, so at high `--rate` a fat-finger decision can depend on whether a trade was processed
  before the next order. Keep the default 20/s for regression baselines.
- **Wall-clock time.** Orders are stamped with the current time rather than the historical one.
  Time-based compliance rules (market hours) are evaluated at replay time. Compliance results are
  not part of the report.
- **Original pacing is not reproduced.** `--rate` is a fixed rate; tag 52 (SendingTime) is
  ignored.

For a reproducible baseline, record and compare on a freshly reset pipeline
(`scripts/cleanup.sh`, or the `reset-pipeline-state` workflow), with the same risk limits in
`docker-compose.yml`.
