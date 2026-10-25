# FixFlux Operations Runbook

Production runbook for on-call engineers and automated SRE agents. Each alert section is a stable
anchor intended for use as an Alertmanager `runbook_url` annotation, e.g.
`https://github.com/NEMETOM/python-engineering-lab/blob/main/fixflux/OPERATIONS.md#2-kafkaconsumerlaghigh`.

Every command, metric, consumer group and container name in this file is taken from the repo as it
exists (`docker-compose.yml`, `infrastructure/monitoring/`, `services/*/src/`). Where an alert or
procedure was requested but the underlying component does not exist, this file says so explicitly
instead of inventing one. Do not "fill in" those gaps during an incident.

---

## 0. Alert index

| Alert                          | Defined in                  | Severity | Status                                                                                       |
|--------------------------------|-----------------------------|----------|----------------------------------------------------------------------------------------------|
| `KafkaConsumerLagHigh`         | `prometheus_alerts.yml`     | warning  | Live. Requested as `KafkaConsumerLagSpike` - same alert, real name is `KafkaConsumerLagHigh`. |
| `MatchingEngineDown`           | `prometheus_alerts.yml`     | critical | Live. `up{job="matching-engine"} == 0` for 1m. Section 3. Real replacement for the requested `StatefulStorePodCrash`. |
| `MatchingEngineP99LatencyHigh` | `prometheus_alerts.yml`     | warning  | Live. No dedicated section yet; check section 2 (`matching-engine` lag) and host memory/CPU first. |
| `StatefulStorePodCrash`        | not defined                 | -        | **No such alert.** Procedure in section 3 covers matching-engine crash/restart.               |
| `MiFIDRealTimeReportingBreach` | not defined                 | -        | **Not operable.** No reporting service, APA gateway or latency metric exists. See section 4.  |
| `TradeStore5xxRateHigh`        | `prometheus_alerts.yml`     | critical | Live. Not covered here yet.                                                                   |
| `ComplianceViolationRateSpike` | `prometheus_alerts.yml`     | warning  | Live. Not covered here yet.                                                                   |
| trade-store SLO burn alerts    | `prometheus_slo_rules.yml`  | page/ticket | Live. See `SLO.md`.                                                                        |

**Paging is not wired.** Every receiver in `alertmanager.yml` is an empty placeholder. Alerts are
only visible at `http://<host>:9093`. Nobody is woken up by any alert in this table today.

---

## 1. Environment and access

### 1.1 Deployment topology

- Single DigitalOcean droplet (2 vCPU / 4 GB), all services in one `docker compose` project.
  Access details: `DROPLET_ACCESS.md`.
- Repo on the droplet: `~/python-engineering-lab/fixflux`.
- Live profiles: `--profile full --profile monitoring` (from `.github/workflows/deploy.yml`).
- Broker: **Redpanda** v23.3.21 (Kafka API compatible). The Apache Kafka shell tools
  (`kafka-consumer-groups.sh` etc.) are **not installed** anywhere in the stack. Use `rpk` inside
  the `redpanda` container instead - equivalents are given below.
- `k8s/` and `helm/` manifests exist in the repo but are **not** the deployed target. There is no
  cluster to run `kubectl` against. All commands below are `docker compose`.

```bash
ssh -i ~/.ssh/fixflux_do root@<droplet-ip>
cd ~/python-engineering-lab/fixflux
alias dc='docker compose --profile full --profile monitoring'
alias rpk='docker compose exec -T redpanda rpk'
```

### 1.2 Endpoints

| Component             | Port (host) | Purpose                                   |
|-----------------------|-------------|-------------------------------------------|
| Prometheus            | 9090        | Metrics, alert state                      |
| Alertmanager          | 9093        | Fired alerts, silences                    |
| Grafana               | 3000        | Dashboards (Loki logs, Tempo traces)      |
| matching-engine       | 8003        | `/metrics` only - no REST API             |
| risk-service          | 8004        | `/metrics` only                           |
| trade-store           | 8000        | `GET /trades`, `/metrics`                 |
| compliance-api        | 8010        | FixFlux Console (FIX injector, rule admin)|
| compliance-consumer   | 8011        | `/metrics` only                           |

### 1.3 Consumer groups (source: `create_consumer(...)` call sites)

| Group                  | Topic                         | Container             |
|------------------------|-------------------------------|-----------------------|
| `order-service`        | `raw_orders`                  | order-service         |
| `risk-service`         | `raw_orders`                  | risk-service          |
| `compliance-raw`       | `raw_orders`                  | compliance-consumer   |
| `compliance-validated` | `validated_orders`            | compliance-consumer   |
| `matching-engine`      | `risk_approved_orders`        | matching-engine       |
| `market-data-service`  | `order_book_updates`, `trades`| market-data-service   |
| `trade-store`          | `trades`                      | trade-store-consumer  |
| `reporting-service`    | `trades`                      | reporting-service     |

All consumers use `auto_offset_reset="earliest"` and `enable_auto_commit=True`
(`shared/infrastructure/kafka_client.py`). Consequence: offsets are committed on a timer, not after
successful processing. A crash can re-deliver a small window of messages; a swallowed exception
skips a message permanently.

### 1.4 Standard first five minutes (any alert)

```bash
dc ps                                            # anything not "Up"? any restarts?
docker stats --no-stream                         # memory pressure on a 4 GB host
df -h / && docker system df                      # disk
rpk cluster health
curl -s localhost:9093/api/v2/alerts | python3 -m json.tool | head -60
```

---

## 2. KafkaConsumerLagHigh

> Requested as `KafkaConsumerLagSpike`. The deployed alert is `KafkaConsumerLagHigh`.

### 2.1 Alert definition

```yaml
expr: kafka_consumergroup_lag_sum > 1000
for: 5m
labels: { severity: warning }
```

Source metric: `danielqsj/kafka-exporter` v1.7.0 (`kafka-exporter` container, scrape job
`kafka-exporter`). Labels: `consumergroup`, `topic`.

### 2.2 Symptoms

- Lag on `compliance-raw` / `compliance-validated`: audit rows and violations in Postgres fall
  behind live order flow; the compliance admin panel shows stale data. Order flow itself is
  **not** blocked - compliance is passive surveillance.
- Lag on `matching-engine`: fills and execution reports stop or trail; `trades_executed_total`
  flattens; Grafana market data appears frozen.
- Lag on `trade-store`: `GET /trades` misses recent fills while `trades_executed_total` keeps rising.

### 2.3 Critical constraint: single partition

`raw_orders`, `risk_approved_orders` and `trades` are single-partition (verified via
`rpk topic describe`, see `.claude/instructions/system_architecture.md`). Other topics are created
the same way and are almost certainly single-partition too - verify before relying on it.

**Scaling consumer containers does not reduce lag on a single-partition topic.** Within one group,
one partition is assigned to exactly one member. Extra replicas sit idle and add rebalance churn.
Throughput per group is bounded by one process. Do not scale as a first response.

### 2.4 Diagnosis

**Step 1 - Which group, which topic, how fast is it moving?**

```bash
curl -s 'localhost:9090/api/v1/query' \
  --data-urlencode 'query=kafka_consumergroup_lag_sum' | python3 -m json.tool

# Is lag growing or draining? (negative = draining)
curl -s 'localhost:9090/api/v1/query' \
  --data-urlencode 'query=deriv(kafka_consumergroup_lag_sum[10m])' | python3 -m json.tool
```

**Step 2 - Offsets and group membership** (`rpk` equivalent of `kafka-consumer-groups.sh --describe`)

```bash
rpk group list
rpk group describe compliance-raw
rpk group describe compliance-validated
rpk group describe matching-engine
```

Read the output:

| Observation                                      | Meaning                                          |
|--------------------------------------------------|--------------------------------------------------|
| `STATE Empty`, no members                        | Consumer process is dead or never joined. Go to step 3. |
| `STATE Stable`, `CURRENT-OFFSET` advancing slowly | Consumer alive but slow. Go to step 4.           |
| `STATE PreparingRebalance` repeatedly            | Members flapping (crash loop, or session timeouts). Go to step 3. |
| `CURRENT-OFFSET` not moving, member present      | Consumer thread hung or dead inside a live process. Go to step 3. |

**Step 3 - Is the consumer actually running?**

```bash
dc ps compliance-consumer matching-engine trade-store-consumer
docker inspect --format '{{.Name}} restarts={{.RestartCount}} oom={{.State.OOMKilled}} exit={{.State.ExitCode}}' \
  $(dc ps -q compliance-consumer matching-engine trade-store-consumer)
dc logs --since 30m compliance-consumer | grep -Ei 'error|exception|traceback' | tail -50
```

`compliance-consumer` specific failure mode: it runs `compliance-raw` and `compliance-validated`
as two daemon threads in one process and `join()`s `raw_orders_thread` first. If the
`validated_orders` thread dies from an exception raised outside its per-message `try`
(e.g. a broker error in the iterator), the container stays `Up` and `compliance-raw` keeps
working, but `compliance-validated` lag grows without bound. Confirm by checking that only one
group has lag and that the log shows a traceback not prefixed by `Failed to process message`.

**Step 4 - Slow consumer: where is the time going?**

compliance-consumer does a Postgres write per event. The most likely bottleneck is the database,
not the network.

```bash
docker compose exec -T postgres psql -U fixuser -d fixdb -c \
  "SELECT pid, state, wait_event_type, wait_event, now()-query_start AS age, left(query,80)
     FROM pg_stat_activity WHERE datname='fixdb' ORDER BY age DESC NULLS LAST LIMIT 15;"

docker compose exec -T postgres psql -U fixuser -d fixdb -c \
  "SELECT count(*) FROM pg_locks WHERE NOT granted;"

docker stats --no-stream postgres compliance-consumer redpanda
```

Network / broker reachability from the consumer's network namespace:

```bash
docker compose exec -T compliance-consumer python -c \
  "import socket,time;t=time.time();socket.create_connection(('redpanda',9092),3);print(f'{(time.time()-t)*1000:.1f} ms')"
dc logs --since 30m compliance-consumer | grep -Ei 'timeout|NoBrokersAvailable|KafkaTimeoutError|Rebalanc' | tail
rpk cluster health
```

Traces: in Grafana, Explore -> Tempo, search `service.name=matching-engine` (or the lagging
service) and sort by duration to see per-message processing time.

### 2.5 Remediation

Apply in order. Stop at the first step that makes `deriv(kafka_consumergroup_lag_sum[10m])` negative.

**R1 - Dead/hung consumer: restart the single container.** Safe: offsets are committed in Redpanda,
the restarted consumer resumes from the last committed offset (a few messages may be re-delivered).

```bash
rpk group describe compliance-validated > /root/incident-$(date +%s)-offsets-before.txt
dc restart compliance-consumer
watch -n 5 'docker compose exec -T redpanda rpk group describe compliance-validated'
```

**Do not restart `matching-engine` to fix lag** without reading section 3 first - a restart
discards the in-memory order book.

**R2 - Database-bound compliance consumer.** Terminate long-running blocking queries identified in
step 4 (`SELECT pg_terminate_backend(<pid>);`), then re-check lag. If the host is memory-starved,
stop non-critical containers to free headroom:

```bash
dc stop market-data-api grafana        # dashboards only; no data loss
```

**R3 - Fetch-size tuning.** Not available as a runtime knob. `create_consumer()` in
`shared/infrastructure/kafka_client.py` passes no `fetch_*` / `max_poll_records` settings and reads
none from the environment. Changing them is a code change to a factory every service uses and
must go through a PR and the normal deploy, not a live edit. On a single partition with a
per-message Postgres write, fetch tuning is unlikely to be the bottleneck anyway.

**R4 - Scaling (only for topics proven to have more partitions than consumers).**

```bash
rpk topic describe validated_orders        # check PARTITIONS first
```

If and only if `PARTITIONS > 1`:

```bash
dc up -d --no-recreate --scale compliance-consumer=2 compliance-consumer
```

Caveat: `compliance-consumer` publishes host port `8011`; a second replica will fail to bind it.
Scaling this service requires removing the fixed host-port mapping first - another code change, not
a live action. For single-partition topics, the real fix is repartitioning, which is a planned
change (see `PERFORMANCE_BOTTLENECKS.md`), not an incident action.

### 2.6 Rollback

**Rolling back a scale-out:**

```bash
dc up -d --no-recreate --scale compliance-consumer=1 compliance-consumer
rpk group describe compliance-validated     # expect STATE Stable, 1 member
```

Scaling down triggers one rebalance. Committed offsets are stored per group/partition in the broker,
not per member, so removing a member does not move or corrupt them. The surviving member resumes
from the group's last commit.

**Rolling back an offset change** (only if someone ran `rpk group seek` during the incident):

Offsets can only be changed while the group has no active members.

```bash
dc stop compliance-consumer
rpk group describe compliance-validated     # must show STATE Empty
# Restore from the file captured in R1. Format per line: <topic> <partition> <offset>
#   validated_orders 0 18234
rpk group seek compliance-validated --to-file /root/restore-offsets.txt
dc start compliance-consumer
```

Never seek a group while its consumer is running, and never seek `matching-engine` without
section 3.4.

### 2.7 Exit criteria

- `kafka_consumergroup_lag_sum` below 1000 for the affected group for 10 minutes; alert resolved
  in Alertmanager.
- For compliance groups: confirm no permanently skipped messages by grepping
  `Failed to process message` in logs for the incident window. Each hit is a missing audit
  record and must be listed in the incident report.

---

## 3. Matching-engine crash / restart

> Alert: `MatchingEngineDown` (`up{job="matching-engine"} == 0` for 1m, severity critical).
> Requested as `StatefulStorePodCrash`. **No alert by that name exists, and there is no stateful
> store, lock file or persistent volume behind the matching engine.** This section covers what
> actually happens when the `matching-engine` container crashes.

### 3.1 How state actually works

- The order book is two plain Python lists per symbol, held in process memory
  (`services/matching-engine/src/matching_engine/order_book.py`). Nothing is persisted.
- The container has no volume and no REST API (port 8003 is `/metrics` only).
- The consumer auto-commits offsets on `risk_approved_orders`. On restart it resumes from the last
  committed offset with an **empty book**. Every resting (unfilled) order that arrived before the
  crash is gone. The engine will not match against them and will not emit cancels for them.
- `trade_id` is a fresh `uuid4()` each time a trade is generated (`engine.py`). Replaying input
  produces **new** trade IDs for the same economic trades, and `trade-store`'s primary key on
  `trade_id` will not deduplicate them.

### 3.2 Symptoms and detection

- `trades_executed_total` flat while `kafka_messages_consumed_total{service="risk-service"}` rises.
- `matching-engine` lag growing (section 2 alert fires after 5 minutes at >1000 messages).
- `orders_in_book` drops to 0 for all symbols after a restart.
- `up{job="matching-engine"} == 0` - fires `MatchingEngineDown` after 1 minute. Note `up` is only
  0 while the process is unreachable; with `restart: on-failure` a fast crash loop can flap between
  scrapes, so also check `RestartCount` in 3.3.
- REST timeouts are not a symptom of this failure: matching-engine has no REST surface. trade-store
  and compliance-api stay up independently.

### 3.3 Diagnosis

```bash
dc ps matching-engine
docker inspect --format 'restarts={{.RestartCount}} oom={{.State.OOMKilled}} exit={{.State.ExitCode}} started={{.State.StartedAt}}' \
  $(dc ps -q matching-engine)
dc logs --since 1h matching-engine | grep -Ei 'traceback|error|killed' -A 15 | tail -80
```

| Exit code / flag  | Likely cause                                   | Check                                     |
|-------------------|------------------------------------------------|-------------------------------------------|
| `oom=true` / 137  | Host or container memory exhausted             | `docker stats --no-stream`, `free -m`, `dmesg -T \| grep -i oom \| tail` |
| 1 + traceback     | Bad message (e.g. non-numeric `price`/`quantity`) | Traceback in logs; message at the committed offset |
| Repeated restarts, same traceback | Poison message re-delivered after each crash | `rpk group describe matching-engine` - offset not advancing |

Memory and disk audit:

```bash
free -m
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}'
df -h / /var/lib/docker
docker system df -v | head -40
rpk cluster logdirs describe 2>/dev/null || docker compose exec -T redpanda du -sh /var/lib/redpanda/data
```

Inspect the message at the stuck offset (poison message):

```bash
rpk group describe matching-engine          # note CURRENT-OFFSET, e.g. 4211
rpk topic consume risk_approved_orders -p 0 -o 4211 -n 1
```

### 3.4 Remediation

**Decision first.** Choose one, record it in the incident channel, and do not mix them.

**Option A - Resume with empty book (default for this simulator).**
Fastest, no duplicate trades, resting orders are lost.

```bash
dc up -d matching-engine
dc logs -f matching-engine | grep -m1 'metrics server started'
curl -s localhost:8003/metrics | grep -E '^orders_in_book|^trades_executed_total' | head
```

Record in the incident report: the time window of lost resting orders (from the last `orders_in_book`
values in Prometheus before the crash).

**Option A' - Poison message.** If the crash loops on one message, skip exactly that one offset:

```bash
dc stop matching-engine
rpk group describe matching-engine          # must show STATE Empty; note CURRENT-OFFSET N
rpk topic consume risk_approved_orders -p 0 -o <N> -n 1 > /root/poison-$(date +%s).json
rpk group seek matching-engine --to-file /dev/stdin <<< "risk_approved_orders 0 <N+1>"
dc start matching-engine
```

The skipped order is a client order that will never get a fill or reject. Attach the saved JSON to
the incident.

**Option B - Rebuild the book by full replay.** Only if resting-order loss is unacceptable. This
re-matches every approved order in retention and **will regenerate every historical trade with new
IDs**. Downstream consumers must be fenced off or the trades table and market data are corrupted.

Preconditions:

```bash
rpk topic describe risk_approved_orders -c | grep -E 'retention|cleanup'   # replay covers retention only
rpk topic describe trades -p                                                # note HIGH-WATERMARK, call it H
```

Procedure:

```bash
# 1. Stop ingress so no live orders interleave with the replay
dc stop fix-gateway compliance-api

# 2. Fence off consumers of the engine's output topics
dc stop trade-store-consumer market-data-service reporting-service
rpk group describe trade-store         > /root/replay-trade-store-before.txt
rpk group describe reporting-service   > /root/replay-reporting-before.txt
rpk group describe market-data-service > /root/replay-mds-before.txt

# 3. Replay
dc stop matching-engine
rpk group seek matching-engine --to start
dc start matching-engine
watch -n 5 'docker compose exec -T redpanda rpk group describe matching-engine'   # wait for LAG 0

# 4. Skip the replayed duplicates on downstream groups
rpk group seek trade-store         --to end --topics trades
rpk group seek market-data-service --to end
rpk group seek reporting-service   --to end --topics trades   # else every replayed trade is reported again under a new trade_id

# 5. Resume
dc start trade-store-consumer market-data-service reporting-service fix-gateway compliance-api
```

Known residual effects of Option B (record them, do not try to undo them live):
- Duplicate fill execution reports on `execution_reports` (no consumer group is fenced for this
  topic in the repo, but any external FIX client reading it will see repeats).
- Orders that expired out of retention are not in the rebuilt book.

### 3.5 Rollback

There is no previous "state volume configuration" to roll back to. Rollback means code or offsets.

**If the crash started after a deploy** (check `git log -1 --format='%h %cI'` against the first
restart in `docker inspect`):

```bash
git log --oneline -5 -- services/matching-engine shared
git checkout <last-good-sha> -- services/matching-engine shared
dc build matching-engine && dc up -d matching-engine
```

This is a temporary on-host hotfix. The next push to `main` redeploys `HEAD` and undoes it, so
follow up with a `git revert` PR on `main`.

**If Option B replay loops or fails mid-way:** stop matching-engine, restore each fenced group from
the files captured in step 2, and fall back to Option A.

```bash
dc stop matching-engine trade-store-consumer market-data-service reporting-service
# Rebuild /root/restore-*.txt as "<topic> <partition> <offset>" lines from the captured describe output
rpk group seek trade-store         --to-file /root/restore-trade-store.txt
rpk group seek market-data-service --to-file /root/restore-mds.txt
rpk group seek reporting-service   --to-file /root/restore-reporting.txt
rpk group seek matching-engine     --to end      # Option A: empty book, no further replay
dc start matching-engine trade-store-consumer market-data-service reporting-service fix-gateway compliance-api
```

### 3.6 Exit criteria

- `up{job="matching-engine"} == 1`, `RestartCount` stable for 15 minutes.
- `matching-engine` group lag 0; `trades_executed_total` increasing with new flow.
- Decision (A / A' / B) and lost/skipped orders recorded in the incident report.

---

## 4. MiFIDRealTimeReportingBreach

> **Not operable.** This alert was requested but cannot be supported by the current system.
> This section exists so that an on-call engineer or agent following a `runbook_url` here gets a
> clear answer instead of a fabricated procedure.

### 4.1 What exists and what does not

| Requested component                       | Present?                                                    |
|-------------------------------------------|-------------------------------------------------------------|
| Post-trade reporting service              | Yes: `reporting-service` (consumes `trades`, writes `regulatory_reports`) |
| Reporting latency metric                  | Yes, under a different name: `regulatory_report_latency_seconds` (histogram, 60s bucket) |
| Primary / secondary APA gateway (mock or real) | No. Reports are stored, never published                 |
| Routing variable for APA endpoint selection | No                                                        |
| Alert rule `MiFIDRealTimeReportingBreach` | No                                                          |

Reporting latency here means trade execution to report creation in `regulatory_reports`, not to
APA acknowledgement. Late rows are flagged with `deadline_breached = true` (more than 60s, RTS 1
Art. 14(1)(a)) and are still stored.

Read-only checks while this alert doesn't exist:

```bash
# Breach count and rate of late reports
curl -s 'localhost:9090/api/v1/query' --data-urlencode \
  'query=sum(rate(regulatory_report_latency_seconds_count[5m])) - sum(rate(regulatory_report_latency_seconds_bucket{le="60.0"}[5m]))' \
  | python3 -m json.tool

docker compose exec -T postgres psql -U fixuser -d fixdb -c \
  "SELECT status, deadline_breached, count(*) FROM regulatory_reports GROUP BY 1, 2 ORDER BY 1, 2;"

dc logs --since 30m reporting-service | grep 'regulatory_report |' | tail
```

A breach is almost always upstream lag: reporting-service only sees a trade after matching-engine
produces it. Check `consumergroup="reporting-service"` lag (section 2) first. A Postgres outage
makes the service retry with backoff, which also shows up as lag, not as lost reports.

### 4.2 If this alert fires anyway

It was added outside this repo. Treat it as a misconfiguration:

```bash
grep -rn MiFIDRealTimeReportingBreach infrastructure/monitoring/
curl -s localhost:9090/api/v1/rules | python3 -m json.tool | grep -n -A5 MiFIDRealTime
```

Silence it in Alertmanager with a comment pointing to this section, and open an issue.

### 4.3 Closest real latency signal

`new_to_fill_latency_seconds` (histogram, label `side`) measures wall-clock time from risk-service's
New ack to the matching-engine Fill. It is an execution latency, not a reporting latency, and has no
regulatory threshold attached.

```bash
curl -s 'localhost:9090/api/v1/query' --data-urlencode \
  'query=histogram_quantile(0.99, sum(rate(new_to_fill_latency_seconds_bucket[5m])) by (le, side))' \
  | python3 -m json.tool
```

If it is elevated, the cause is almost always matching-engine lag: go to section 2 with
`consumergroup="matching-engine"`.

### 4.4 Prerequisites before this runbook can be written

1. ~~A reporting service consuming `trades`~~ (done: `reporting-service`); publishing to an APA
   endpoint is still missing.
2. A latency histogram measured from trade execution to APA acknowledgement. Today's
   `regulatory_report_latency_seconds` stops at report creation.
3. A configurable primary/fallback endpoint with a defined, tested switchover mechanism
   (env var + container recreate is the pattern this repo would support; there is no in-memory
   config reload mechanism in any service today).
4. An alert rule on (2), with a `runbook_url` pointing here.

---

## 5. Linking alerts to this file

`runbook_url` annotations in `prometheus_alerts.yml`:

| Alert                          | `runbook_url` anchor                  |
|--------------------------------|---------------------------------------|
| `KafkaConsumerLagHigh`         | `#2-kafkaconsumerlaghigh`             |
| `MatchingEngineDown`           | `#3-matching-engine-crash--restart`   |
| `MatchingEngineP99LatencyHigh` | none - no dedicated section yet       |
| `TradeStore5xxRateHigh`        | none - no dedicated section yet       |
| `ComplianceViolationRateSpike` | none - no dedicated section yet       |

Base URL: `https://github.com/NEMETOM/python-engineering-lab/blob/main/fixflux/OPERATIONS.md`.
Only link an alert once a section genuinely covers it. When adding a section, keep the heading text
stable - the anchor is derived from it, and renaming it breaks every existing link.

After editing alert rules on the droplet, reload Prometheus (`--web.enable-lifecycle` is set):

```bash
curl -X POST localhost:9090/-/reload
curl -s localhost:9090/api/v1/rules | python3 -m json.tool | grep runbook_url
```

Run the `predeploy-check` skill before pushing changes under `infrastructure/monitoring/`.
