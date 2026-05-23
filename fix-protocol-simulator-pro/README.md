# FIX Protocol Simulator Pro

[![Fix Gateway CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/fix-gateway.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/fix-gateway.yml)
[![Order Service CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/order-service.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/order-service.yml)
[![Matching Engine CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/matching-engine.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/matching-engine.yml)
[![Market Data Service CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/market-data-service.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/market-data-service.yml)
[![Trade Store CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/trade-store.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/trade-store.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/badge/linting-ruff-orange.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

An event-driven exchange simulator that models a real-world order flow pipeline using the FIX protocol - from client message ingestion through order validation, price-time priority matching, market data publication, and trade persistence. Built with Python microservices, Redpanda (Kafka-compatible), PostgreSQL, and Docker, following 12-Factor, Hexagonal Architecture, and Domain-Driven Design principles.

> Designed to reflect the architecture of production trading systems at firms such as Bloomberg, Fidessa, Coinbase, and Kraken - where FIX protocol ingestion, Kafka-based event routing, and microservice-bounded contexts are standard engineering practice.

---

## Why This Project Exists

FIX (Financial Information eXchange) is the dominant messaging protocol in equities, FX, and derivatives trading. Understanding how an order flows from a client-facing gateway through validation, matching, and persistence is foundational knowledge for anyone building or testing systems in capital markets.

This project was built to go beyond surface-level familiarity with these concepts - to implement the actual mechanics: session management, event-driven order routing, a stateful matching engine, change-detected market data publishing, and a queryable trade history API. Every design decision follows patterns used in real trading infrastructure.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    External Clients                      │
│           FIX File Drop  /  TCP Socket Client           │
└──────────────────────────┬──────────────────────────────┘
                           │  FIX tag=value messages (pipe-delimited)
                           ▼
              ┌────────────────────────┐
              │      FIX Gateway       │  Session management, FIX parsing,
              │                        │  Logon / Heartbeat / NewOrderSingle
              └────────────┬───────────┘
                           │ raw_orders (Kafka)
                           ▼
              ┌────────────────────────┐
              │     Order Service      │  Business rule validation,
              │                        │  UUID assignment, event enrichment
              └────────────┬───────────┘
                           │ validated_orders (Kafka)
                           ▼
              ┌────────────────────────┐
              │    Matching Engine     │  Price-time priority order book,
              │                        │  trade execution, book snapshots
              └──────┬─────────────────┘
                     │
          ┌──────────┴──────────┐
          │ trades (Kafka)      │ order_book_updates (Kafka)
          ▼                     ▼
┌──────────────────┐   ┌──────────────────────┐
│   Trade Store    │   │  Market Data Service  │
│                  │   │                       │
│  PostgreSQL      │   │  Change-detected pub  │
│  FastAPI REST    │   │  to market_data topic │
└──────────────────┘   └──────────────────────┘
```

**Message flow:** Client drops a FIX file → FIX Gateway parses and publishes → Order Service validates and enriches → Matching Engine applies price-time priority → matched trades fan out to Trade Store (persistence) and Market Data Service (real-time snapshot) in parallel.

---

## Key Features

- **FIX Protocol Ingestion** - Parses `tag=value` pipe-delimited FIX messages. Identifies Logon (`35=A`), Heartbeat (`35=0`), and NewOrderSingle (`35=D`) message types with per-client session state tracking.
- **Event-Driven Pipeline** - Fully decoupled services communicating exclusively through Redpanda (Kafka-compatible) topics. No direct service-to-service calls.
- **Price-Time Priority Matching Engine** - Stateful in-memory order book. BUY orders match against the best ask; SELL orders match against the best bid. Partial fills and remainder queuing supported.
- **Change-Detected Market Data Publishing** - Market data snapshots are only published when bid, ask, or last trade price actually changes - no unnecessary events.
- **Trade Persistence + REST API** - Every matched trade is persisted to PostgreSQL via a Kafka consumer. A FastAPI service exposes `GET /trades`, `GET /trades/{id}`, and `GET /health` with Swagger UI.
- **Shared Internal Platform Library** - Cross-service Pydantic v2 schemas, Kafka client factory, structured JSON logging, SQLAlchemy session management, and typed exceptions - installed as an editable package across all services.
- **Three-Layer Testing** - Unit tests (pytest), component BDD tests (behave + Gherkin), and infrastructure integration tests covering both PostgreSQL persistence and the Kafka pipeline.
- **Five Independent CI/CD Pipelines** - Each service has its own GitHub Actions workflow with separate test, lint, and Docker build stages. Daily scheduled runs catch dependency drift.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Message Broker | Redpanda v23.3.21 (Kafka-compatible, no JVM, no Zookeeper) |
| Database | PostgreSQL 15 |
| API Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy |
| Schema Validation | Pydantic v2 |
| Containerisation | Docker + Docker Compose v2 |
| Testing | pytest, behave (BDD/Gherkin) |
| Static Analysis | ruff, black, isort, mypy |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus v2.51 + Grafana v10.4 (Docker, auto-provisioned) |
| Packaging | pyproject.toml (PEP 517/518), src layout |

---

## CI/CD Pipeline

Each of the five services has an independent GitHub Actions workflow. Pipelines are triggered on:

- **Push** - path-filtered per service (only the affected service's pipeline runs)
- **Pull request** - same path filtering, enforced on every PR
- **Scheduled** - daily at 06:00 UTC to catch dependency drift and upstream regressions
- **Manual dispatch** - via the GitHub Actions tab

Each pipeline runs four stages in sequence:

```
Checkout → Install dependencies → Run pytest (coverage) → Lint → Build Docker image
```

**Lint stage** runs four checks in sequence - any failure blocks the build:

```bash
python -m ruff check .          # fast linting
python -m black --check .       # formatting
python -m isort --check-only .  # import ordering
python -m mypy src/ --ignore-missing-imports  # type checking
```

Every service follows the same pipeline:

| Step | |
|---|---|
| Set up job | ✅ |
| Checkout repository | ✅ |
| Set up Python 3.11 | ✅ |
| Install shared module | ✅ |
| Run pytest with coverage | ✅ |
| Lint (ruff, black, isort, mypy) | ✅ |
| Build Docker image | ✅ |
| Post Set up Python 3.11 | ✅ |
| Post Checkout repository | ✅ |
| Complete job | ✅ |

---

## Design Standards

### Twelve-Factor App

| Factor | Implementation |
|---|---|
| Config | All runtime config via environment variables (`KAFKA_BROKER`, `DATABASE_URL`, `LOG_LEVEL`) |
| Backing services | Kafka and PostgreSQL treated as attached resources |
| Build / release / run | Per-service Dockerfiles; docker-compose handles orchestration |
| Processes | Stateless consumers; Kafka holds all durable inter-service state |
| Logs | Structured JSON to stdout; no log files |

### Hexagonal Architecture (Ports and Adapters)

Infrastructure concerns (Kafka client, database session) are isolated in `infrastructure/` within each service. Domain logic (validator, matching engine, transformer) has no framework dependencies and is independently testable.

### Bounded Contexts (Domain-Driven Design)

Each service owns exactly one bounded context. Services communicate through Kafka events, never via direct calls - consistent with Sam Newman's microservices patterns and Martin Fowler's event-driven architecture guidance.

### Python Packaging (PEP 517/518 + src layout)

Every service uses the `src/` layout recommended by the Python Packaging User Guide, with `pyproject.toml` as the single source of build metadata. This prevents accidental imports of uninstalled packages and cleanly separates source from tests and config.

---

## Project Structure

```
fix-protocol-simulator-pro/
├── docker-compose.yml               # Full-stack orchestration with health-check startup ordering
├── services/
│   ├── fix-gateway/                 # FIX TCP/file ingestion, session management
│   │   ├── src/fix_gateway/
│   │   │   ├── server.py            # TCP socket server
│   │   │   ├── fix_handler.py       # FIX parser (tag=value)
│   │   │   └── session_manager.py   # Per-client session state
│   │   └── tests/                   # unit + BDD tests
│   ├── order-service/               # Validation, enrichment, UUID assignment
│   ├── matching-engine/             # Price-time priority order book + trade execution
│   ├── market-data-service/         # Change-detected snapshot publishing
│   └── trade-store/                 # Kafka consumer + PostgreSQL + FastAPI REST
├── shared/                          # Internal platform library
│   ├── schemas/                     # Pydantic v2 event schemas (OrderEvent, TradeEvent, BookEvent)
│   ├── infrastructure/              # Kafka client factory, SQLAlchemy session, DB setup
│   ├── observability/               # Structured JSON logging + Prometheus metric definitions
│   └── exceptions/                  # Typed exception hierarchy
├── infrastructure/
│   └── monitoring/
│       ├── prometheus.yml           # Scrape config (fix-gateway, matching-engine, trade-store)
│       └── grafana/
│           ├── provisioning/        # Auto-wired datasource + dashboard provider
│           └── dashboards/          # fix_simulator_overview.json (14 panels, 4 rows)
├── clients/
│   └── fix-filedrop-client/         # Local directory watcher - drops FIX files into pipeline
├── data/                            # Sample FIX message files (buy/sell pairs per symbol)
├── tests/
│   └── integration/                 # BDD integration tests (PostgreSQL + Kafka)
└── scripts/                         # Local utility scripts (DB connectivity check, etc.)
```

---

## Services Reference

| Service | Consumes | Produces | Responsibility |
|---|---|---|---|
| **fix-gateway** | - | `raw_orders` | Parses FIX `tag=value` messages, identifies message types, manages per-client sessions |
| **order-service** | `raw_orders` | `validated_orders` | Validates price/quantity/side rules, assigns UUID order ID, drops invalid orders |
| **matching-engine** | `validated_orders` | `trades`, `order_book_updates` | Price-time priority matching, partial fills, order book snapshots on each match |
| **market-data-service** | `trades`, `order_book_updates` | `market_data` | Caches best bid/ask/last trade; publishes snapshot only on change |
| **trade-store** | `trades` | - | Persists trades to PostgreSQL; exposes REST API via FastAPI |
| **shared** | - | - | Internal library: schemas, Kafka factory, logging, DB session, exceptions |

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 24+ (includes Docker Compose v2)
- Python 3.11+ (for the local file-drop watcher only)

### 1. Clone

```bash
git clone https://github.com/NEMETOM/python-engineering-lab.git
cd python-engineering-lab/fix-protocol-simulator-pro
```

### 2. Start the stack

Services are grouped into profiles:

| Profile | Services |
|---|---|
| _(none)_ | `redpanda`, `postgres` only |
| `pipeline` | + `fix-gateway`, `order-service`, `matching-engine`, `trade-store` |
| `full` | + all of the above + `market-data-service` |
| `monitoring` | + `prometheus`, `grafana` (combine with pipeline or full) |

```bash
# Full stack + monitoring (Prometheus + Grafana)
docker compose --profile full --profile monitoring up --build

# Full stack without monitoring
docker compose --profile full up --build

# Pipeline only (no market data)
docker compose --profile pipeline up --build

# Individual services - depends_on resolved automatically
docker compose up redpanda matching-engine trade-store
```

Redpanda and Postgres expose health checks. Application services wait until both report healthy before starting.

### 3. Verify

```bash
docker compose ps
```

| Container | State | Port |
|---|---|---|
| redpanda | Up (healthy) | 9092 |
| postgres | Up (healthy) | 5433 |
| fix-gateway | Up | 8001 (metrics) |
| order-service | Up | - |
| matching-engine | Up | 8003 (metrics) |
| trade-store | Up | 8000, 8000/metrics |
| prometheus | Up (monitoring profile) | 9090 |
| grafana | Up (monitoring profile) | 3000 |

### 4. REST API

Swagger UI: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/trades` | All trades (optional `?symbol=EURUSD`) |
| `GET` | `/trades/{trade_id}` | Single trade by ID |

> Only matched trades appear in the API. Unmatched orders rest in the matching engine's in-memory order book until a crossing counterpart arrives.

### 5. Run the file-drop watcher (separate terminal)

```bash
pip install -e shared
pip install -e services/fix-gateway

python clients/fix-filedrop-client/watcher.py
```

### 6. Drop a FIX order file

```bash
# Create a buy order
echo "35=D|55=EURUSD|54=1|44=1.09|38=100|" > clients/fix-filedrop-client/filedrop/buy_001.txt

# Create a matching sell order
echo "35=D|55=EURUSD|54=2|44=1.09|38=100|" > clients/fix-filedrop-client/filedrop/sell_001.txt
```

The watcher detects each file, publishes to `raw_orders`, and moves it to `processed/` on success or `rejected/` on validation failure. Ready-to-use sample files are in `data/`.

---

## FIX Message Format

FIX messages in this simulator use pipe (`|`) as the field delimiter. Each field is a `tag=value` pair:

```
35=D|49=CLIENT1|55=EURUSD|54=1|40=2|44=1.0900|38=100|
```

| Tag | Field | Value |
|---|---|---|
| `35` | MsgType | `D` = NewOrderSingle |
| `49` | SenderCompID | Client identifier |
| `55` | Symbol | Instrument (EURUSD, BTCUSD, AAPL) |
| `54` | Side | `1` = Buy, `2` = Sell |
| `40` | OrdType | `2` = Limit |
| `44` | Price | Limit price |
| `38` | OrderQty | Quantity |

A matched trade requires a crossing counterpart - a BUY at price >= the SELL's asking price (or vice versa). Example matching pair:

```
# Buy EURUSD @ 1.09
35=D|55=EURUSD|54=1|44=1.09|38=100|

# Sell EURUSD @ 1.09 - crosses with the buy above, trade executes
35=D|55=EURUSD|54=2|44=1.09|38=100|
```

Invalid message example (missing side tag `54`):

```
35=D|55=BTCUSD|44=50000|38=1|
```

Result: moved to `rejected/`, error logged by the order service.

---

## Testing

### Unit Tests

Each service has isolated unit tests with mocked infrastructure (Kafka, DB). Coverage is reported per service.

```bash
cd services/matching-engine && python -m pytest -v
cd services/order-service   && python -m pytest -v
cd services/trade-store     && python -m pytest -v
cd services/market-data-service && python -m pytest -v
cd services/fix-gateway     && python -m pytest -v
cd shared                   && python -m pytest -v
```

### BDD Component Tests (Gherkin)

Business behaviour is specified as Gherkin feature files and executed with behave. Feature files and step implementations are co-located under `tests/bdd/` in each service.

```bash
cd services/matching-engine && python -m behave tests/bdd/features/
cd services/order-service   && python -m behave tests/bdd/features/
cd services/trade-store     && python -m behave tests/bdd/features/
```

Example scenario from the matching engine:

```gherkin
Scenario Outline: Buy order matches against resting sell
  Given an order book with a sell order at price <ask>
  When a buy order arrives at price <bid>
  Then a trade is executed at price <ask>

  Examples:
    | ask   | bid   |
    | 100.0 | 100.0 |
    | 100.0 | 101.0 |
```

### Integration Tests

Integration tests exercise real infrastructure. Start the required services first:

```bash
# PostgreSQL only (persistence tests)
docker compose up -d postgres

# PostgreSQL + Redpanda (full pipeline tests)
docker compose up -d postgres redpanda
```

```bash
cd tests/integration

# All integration tests
python -m behave features/

# Persistence only (no Kafka required)
python -m behave features/ --tags="@integration" --tags="~@needs_kafka"

# Kafka pipeline tests
python -m behave features/ --tags="@needs_kafka"
```

---

## Environment Variables

| Variable | Default | Used by |
|---|---|---|
| `KAFKA_BROKER` | `localhost:9092` | All services |
| `DATABASE_URL` | _(reads config.yaml)_ | trade-store |
| `LOG_LEVEL` | `INFO` | All services |
| `LOG_FORMAT` | `plain` | All services (`json` for structured logs) |
| `PUBLISH_INTERVAL` | `10` | market-data-service |

---

## Monitoring & Observability

The simulator ships with a full Prometheus + Grafana monitoring stack, reflecting production observability practice in trading systems.

### Stack

| Component | Role |
|---|---|
| **Prometheus** `v2.51` | Scrapes metrics from each service every 15 s; retains time-series data |
| **Grafana** `v10.4` | Pre-provisioned dashboard with 4 collapsible rows and 14 panels |
| **prometheus-client** `>=0.20` | Python library; embedded HTTP server (fix-gateway, matching-engine) and ASGI endpoint (trade-store) |

### Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│                                                             │
│  fix-gateway:8001/metrics  ──────────┐                      │
│  matching-engine:8003/metrics ───────┼──► Prometheus:9090   │
│  trade-store:8000/metrics ───────────┘        │             │
│                                               │             │
│                                          Grafana:3000        │
└─────────────────────────────────────────────────────────────┘
```

Prometheus scrapes all three targets inside the Docker network. Grafana reads Prometheus as its datasource (auto-provisioned - no manual setup).

### Start the monitoring stack

```bash
# Full pipeline + monitoring
docker compose --profile full --profile monitoring up --build

# Monitoring only (scrapes running services from a previous session)
docker compose --profile monitoring up
```

| UI | URL | Credentials |
|---|---|---|
| Grafana | `http://localhost:3000` | admin / admin |
| Prometheus | `http://localhost:9090` | - |
| Raw metrics (trade-store) | `http://localhost:8000/metrics` | - |
| Raw metrics (fix-gateway) | `http://localhost:8001/metrics` | - |
| Raw metrics (matching-engine) | `http://localhost:8003/metrics` | - |

### Metrics Reference

| Metric | Type | Labels | Source |
|---|---|---|---|
| `fix_messages_received_total` | Counter | `msg_type` (logon, heartbeat, new_order) | fix-gateway |
| `fix_messages_parse_errors_total` | Counter | - | fix-gateway |
| `fix_sessions_active` | Gauge | - | fix-gateway |
| `fix_reconnect_attempts_total` | Counter | - | fix-gateway |
| `trades_executed_total` | Counter | `symbol` | matching-engine |
| `order_matching_latency_seconds` | Histogram | - | matching-engine |
| `orders_in_book` | Gauge | `side` (buy, sell) | matching-engine |
| `kafka_messages_consumed_total` | Counter | `topic`, `service` | matching-engine |
| `api_requests_total` | Counter | `endpoint`, `method`, `status_code` | trade-store |
| `api_request_latency_seconds` | Histogram | `endpoint` | trade-store |

All metric definitions live in [`shared/observability/metrics.py`](shared/observability/metrics.py) - a single source of truth importable by any service via `PYTHONPATH`.

### Grafana Dashboard

The pre-provisioned dashboard (`fix_simulator_overview`) has four rows:

| Row | Panels |
|---|---|
| **FIX Gateway** | Messages/sec by type (time series), Active Sessions (stat), Parse Errors/min (stat), Message type distribution (donut) |
| **Matching Engine** | Trades/sec by symbol (time series), Latency P99 (gauge), Latency P50 (gauge), Order book depth - buy vs sell (time series) |
| **Trade Store API** | Request rate (time series), API Latency P99 (gauge), 5xx Error Rate (stat), Latency percentile trends p50/p95/p99 |
| **Kafka Throughput** | Messages consumed/sec (time series), Messages produced/sec (time series) |

### Recommended Screenshots for Portfolio

1. **Grafana overview** - Dashboard with all 4 rows expanded, live data flowing after dropping a batch of sample orders
2. **Matching latency gauge** - P99 < 1 ms demonstrating in-process matching speed
3. **Trade execution spike** - `trades_executed_total` rate climbing when a crossing pair is dropped
4. **Order book depth** - buy/sell gauge showing resting orders accumulate then clear on a match
5. **Prometheus targets** - `http://localhost:9090/targets` showing all 3 scrape targets green (`UP`)

### Extending to Other Services

The order-service and market-data-service follow the identical pattern:

1. Import metrics from `shared.observability.metrics`
2. Call `start_http_server(<port>)` before the consumer loop
3. Add `prometheus-client>=0.20` to `pyproject.toml`
4. Add the scrape target to `infrastructure/monitoring/prometheus.yml`

### Production Observability Notes

- **Histograms over averages** - Latency is tracked as a histogram, enabling P99/P95/P50 queries. Averages hide tail latency and are misleading for SLA analysis.
- **Labels as dimensions** - `symbol`, `msg_type`, `status_code` labels allow Grafana to slice metrics per instrument or endpoint without separate metrics per value.
- **Counter + rate()** - All throughput metrics are counters. Grafana uses `rate()` to compute per-second rates, which handles counter resets (pod restarts) correctly.
- **Gauge for state** - `fix_sessions_active` and `orders_in_book` are gauges - values that go up and down, not monotonic.
- **Separate metrics port** - fix-gateway and matching-engine expose metrics on dedicated ports (8001, 8003), keeping business traffic and observability traffic on separate sockets.

---

## Engineering Highlights

**Protocol-level engineering** - Implements FIX tag=value parsing, message type routing, and per-client session state from scratch. No FIX library dependency.

**Stateful matching engine** - Price-time priority order book with partial fill support. Orders rest in the book until a crossing counterpart arrives. Book state is entirely in-memory, consistent with how real matching engines operate before persistence layers.

**Change-detected event publishing** - The market data service tracks `(best_bid, best_ask, last_trade_price)` as a tuple and suppresses publication if nothing changed - reducing downstream noise without a polling interval.

**Five independent CI pipelines** - Each service is independently deployable and independently tested. CI is path-filtered: only the pipeline for the changed service runs on a given PR. All five run daily on a cron schedule.

**Production-style observability** - Structured JSON logging throughout (INFO for business events, DEBUG for infrastructure noise). Prometheus metrics instrumented across three services; Grafana dashboard auto-provisioned with 14 panels covering FIX message rates, matching latency (P50/P99), order book depth, and API error rates. Monitoring profile starts Prometheus + Grafana alongside the application stack via a single compose command.

**Shared internal library pattern** - Cross-cutting concerns (Pydantic schemas, Kafka factory, SQLAlchemy session, exception hierarchy) are extracted into a versioned internal package, mirroring how platform teams in larger engineering organisations manage shared infrastructure.

---

## Future Improvements

| Area | Detail |
|---|---|
| FIX TCP session | Full logon/heartbeat/logout lifecycle over persistent TCP connections (currently file-drop only) |
| Multi-symbol order book | Per-symbol book isolation - currently all symbols share one book |
| WebSocket market data | Push-based streaming of market data snapshots to connected clients |
| Kubernetes deployment | Helm charts for each service; horizontal scaling of the matching engine |
| OpenTelemetry traces | Distributed tracing across services; correlate a single order through all 4 hops |
| Schema registry | Confluent Schema Registry for Avro/Protobuf event versioning |
| Async I/O | Replace blocking Kafka consumers with asyncio-based consumers (aiokafka) |
| FIX replay | Ability to replay historical FIX message files for backtesting and regression |

---

## License

MIT
