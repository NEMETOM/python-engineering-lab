# Future Enhancements Backlog

Personal backlog for FIX Protocol Simulator Pro - not committed to the repository.
Ordered roughly by effort, with hedge fund / institutional trading relevance in mind.

---

## 1. Kubernetes + Helm Chart

**Why:** Hedge fund infra teams live in Kubernetes. Docker Compose is a local dev tool; Kubernetes is the production target. A proper Helm chart is the single most visible signal that the project is production-oriented.

**What to build:**
- `k8s/` directory with `Deployment`, `Service`, `ConfigMap`, and `Secret` manifests per service
- `HorizontalPodAutoscaler` on the matching engine (scales on CPU/RPS)
- `StatefulSet` for Redpanda (stateful broker needs stable pod identity and persistent volumes)
- Helm chart with `values.yaml` exposing all tuneable knobs (replica counts, resource limits, image tags)
- `kustomize/overlays/` for `dev` / `staging` / `prod` environment differences

**Signals it sends:** You understand the difference between local orchestration and production deployment, stateful vs stateless workloads, and how platform teams manage environment drift.

---

## 2. Per-Symbol Order Book Isolation

**Why:** Currently all symbols share one in-memory `OrderBook` instance. Real matching engines shard by symbol (or instrument group). This means a EURUSD order and a BTCUSD order compete for the same book state - functionally wrong for a multi-asset simulator.

**What to build:**
- Replace `OrderBook` singleton with `dict[str, OrderBook]` keyed by symbol inside `MatchingEngine`
- Each symbol gets independent best bid/ask, fill queue, and book snapshot
- Unlocks realistic cross-asset scenarios (e.g., a quant strategy sending correlated EURUSD + GBPUSD orders)
- Metrics: `orders_in_book` gauge gains a `symbol` label

**Signals it sends:** Awareness of how production matching engines actually partition state - this is a common quant interview topic.

---

## 3. Pre-Trade Risk Limits

**Why:** Hedge funds care more about preventing bad trades than detecting them after the fact. The compliance module catches violations retrospectively. Pre-trade risk is the upstream gate that never lets a violating order reach the matching engine.

**What to build:**
- New lightweight service (or middleware in the order service) that enforces:
  - Gross/net position limits per client and per symbol
  - Notional value limits (price x quantity caps)
  - Fat-finger checks (price more than N% from last trade)
  - Max open order count per client
- Orders that breach a limit are rejected with a reason code before they reach `validated_orders`
- Position state maintained in Redis or in-memory with Kafka-sourced replay on restart

**Signals it sends:** Understanding of the pre-trade risk framework that every prime broker and hedge fund OMS implements (MiFID II Article 17, SEC Rule 15c3-5).

---

## 4. OpenTelemetry Distributed Tracing

**Why:** The current observability stack (Prometheus + structured logging) covers metrics and logs. The third pillar - traces - is missing. A single order touches 4 services; without trace context you cannot correlate what happened to order `O-123` across all hops.

**What to build:**
- Add `opentelemetry-sdk` and `opentelemetry-exporter-otlp` to shared dependencies
- Propagate a `trace_id` field through every Kafka message payload
- Each service creates a child span when it consumes a message, closing it after processing
- Add Jaeger or Tempo to the monitoring Docker Compose profile as the trace backend
- Grafana datasource addition: Tempo linked to Prometheus for trace-to-metrics correlation

**Signals it sends:** The three pillars of observability (metrics, logs, traces) are a standard interview topic. Showing all three in a single project is unusual and memorable.

---

## 5. Execution Algorithms (TWAP / VWAP)

**Why:** Hedge funds do not submit single large orders to an exchange. They use execution algorithms to slice parent orders into child orders over time, minimising market impact. TWAP (time-weighted) and VWAP (volume-weighted) are the industry baseline.

**What to build:**
- New `algo-engine` service that accepts parent orders via a dedicated Kafka topic or REST endpoint
- TWAP: splits a parent order into N equal child orders, scheduled evenly over a time window
- VWAP: weights child order sizes against a reference volume profile (historical or simulated)
- Child orders published to `raw_orders` like any other FIX message
- Parent order state tracked (total filled, average fill price, slippage vs VWAP benchmark)

**Signals it sends:** Direct relevance to execution trading roles at hedge funds and asset managers. Shows you understand that order placement is not atomic.

---

## 6. WebSocket Market Data Streaming

**Why:** The current market data service publishes to a Kafka topic (`market_data`). Real hedge fund market data infrastructure pushes best bid/ask and last trade directly to strategy processes via a streaming connection. WebSocket is the standard for web-accessible real-time feeds.

**What to build:**
- Add a WebSocket endpoint to the market data service (FastAPI supports this natively)
- Each connected client receives a stream of `{ symbol, best_bid, best_ask, last_trade, timestamp }` objects
- Only emit when state changes (change-detection already implemented - reuse that logic)
- Optional: subscription filtering (`?symbol=EURUSD` to receive only EURUSD updates)

**Signals it sends:** Awareness of push-based vs pull-based data distribution, and how live trading systems consume market data without polling.

---

## 7. FIX Execution Reports (35=8)

**Why:** Currently the FIX Gateway only receives orders - it never sends responses back to the client over the TCP session. In a real FIX session, every order receives an `ExecutionReport` (`35=8`) acknowledging receipt, and a second one on fill. Without this, the FIX session lifecycle is incomplete.

**What to build:**
- When a trade is matched, publish a fill event back to the FIX Gateway via Kafka
- FIX Gateway sends `ExecutionReport` (`35=8`) with `OrdStatus=2 (Filled)` or `1 (PartialFill)` back over the TCP connection to the originating client
- Handle the `ExecType` field correctly: `0=New`, `1=PartialFill`, `2=Fill`, `4=Cancelled`
- Adds bidirectional FIX session semantics - closer to how Bloomberg EMSX or a prime broker gateway works

**Signals it sends:** Deep FIX protocol knowledge. Most candidates who claim FIX experience have only read messages, not written the response side.

---

## 8. Backtesting Mode with Historical Replay

**Why:** Strategy evaluation at hedge funds requires replaying historical order flow through the engine at controlled speed to measure fill rates, slippage, and market impact under realistic conditions. The audit trail and dead letter queue infrastructure already in place are the natural foundation.

**What to build:**
- A `replay` CLI that reads a directory of timestamped FIX files (or the compliance audit trail) and feeds them through the pipeline at configurable speed (1x, 10x, 100x real-time)
- Synthetic clock that advances based on message timestamps, not wall clock
- Replay metrics: fill rate, average slippage, rejected order count, P&L per strategy
- Results written to a PostgreSQL `backtest_runs` table with per-run summary and per-order detail

**Signals it sends:** Bridges the gap between a trading infrastructure project and a quantitative finance project - relevant to both platform engineering and quant research roles.

---

## Priority Recommendation

| Priority | Item | Effort | Signal strength |
|---|---|---|---|
| 1 | Kubernetes + Helm | Medium | Very high - every infra conversation starts here |
| 2 | Pre-trade risk limits | Medium | High - directly relevant to trading risk roles |
| 3 | Per-symbol order book | Low-medium | Medium - correctness fix with visible architecture impact |
| 4 | OpenTelemetry tracing | Medium | High - completes the three-pillar observability story |
| 5 | Execution algorithms | Medium-hard | Very high - direct quant fund relevance |
| 6 | WebSocket streaming | Medium | Medium - good portfolio demo material |
| 7 | FIX Execution Reports | Hard | High - demonstrates real FIX protocol depth |
| 8 | Backtesting replay | Hard | Very high for quant research roles |
