<p align="center">
  <img src="docs/FixFlux-Logo.png" width="160" alt="FIXFlux" />
</p>

# FIXFlux | Event-Driven Electronic Trading Platform

[![Fix Gateway CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/fix-gateway.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/fix-gateway.yml)
[![Order Service CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/order-service.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/order-service.yml)
[![Matching Engine CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/matching-engine.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/matching-engine.yml)
[![Market Data Service CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/market-data-service.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/market-data-service.yml)
[![Trade Store CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/trade-store.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/trade-store.yml)
[![Compliance Service CI](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/compliance-service.yml/badge.svg)](https://github.com/NEMETOM/python-engineering-lab/actions/workflows/compliance-service.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/badge/linting-ruff-orange.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
<!-- STATUS_BADGE_START -->
[![Live System Status](https://img.shields.io/badge/Live%20System-Unknown-lightgrey?style=flat-square&logo=prometheus)](https://github.com/NEMETOM/python-engineering-lab)  <!-- Awaiting first automated check -->
<!-- STATUS_BADGE_END -->

---

- Event-driven exchange simulator that models a real-world order flow pipeline using the **FIX protocol**
- Full pipeline: client message ingestion → order validation → **price-time priority matching** → market data publication → trade persistence
- Parallel **RegTech compliance and surveillance module** for real-time rule evaluation and audit trail
- **MiFID II pre-trade risk gate**: notional cap, fat-finger, and position limit checks before orders reach the matching engine
- Built with Python microservices, Redpanda (Kafka-compatible), PostgreSQL, and Docker
- Follows 12-Factor App, Hexagonal Architecture, and Domain-Driven Design principles

> Designed to reflect the architecture of production trading systems at firms such as Bloomberg, Fidessa, Coinbase, and Kraken - where FIX protocol ingestion, Kafka-based event routing, and microservice-bounded contexts are standard engineering practice.

---

## Business Value

For decision makers evaluating trading infrastructure:

- **Regulatory compliance out of the box** - MiFID II pre-trade risk checks and a tamper-evident audit trail mean regulators and compliance officers have the evidence they need, without manual record-keeping
- **Catches costly errors before they execute** - fat-finger and notional cap rules stop erroneous orders at the gate, preventing the kind of trading losses that have cost firms hundreds of millions in publicised incidents
- **Real-time market surveillance** - wash trading detection, rapid-fire order patterns, and off-hours activity are flagged automatically, reducing the compliance team's manual review burden
- **No vendor lock-in** - fully open-source stack (Python, Kafka, PostgreSQL) with no per-seat or per-message licensing fees that proprietary FIX engines typically charge
- **Cloud-ready from day one** - the same codebase runs on a laptop and deploys to Kubernetes with a single Helm command, cutting the gap between development and production

---

## Why This Project Exists

FIX (Financial Information eXchange) is the dominant messaging protocol in equities, FX, and derivatives trading. Understanding how an order flows from a client-facing gateway through validation, matching, and persistence is foundational knowledge for anyone building or testing systems in capital markets.

This project was built to go beyond surface-level familiarity with these concepts - to implement the actual mechanics: session management, event-driven order routing, a stateful matching engine, change-detected market data publishing, and a queryable trade history API. Every design decision follows patterns used in real trading infrastructure.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                       External Clients                        │
│               FIX File Drop  /  TCP Socket Client            │
└──────────────────────────────┬───────────────────────────────┘
                               │  FIX tag=value messages (pipe-delimited)
                               ▼
                  ┌────────────────────────┐
                  │      FIX Gateway       │  Session management, FIX parsing,
                  │                        │  Logon / Heartbeat / NewOrderSingle
                  └────────────┬───────────┘
                               │ raw_orders (Kafka)
               ┌───────────────┤
               │               ▼
               │  ┌────────────────────────┐
               │  │     Order Service      │  Business rule validation,
               │  │                        │  UUID assignment, enrichment
               │  └────────────┬───────────┘
               │               │ validated_orders (Kafka)
               ├───────────────┤
               ▼               ▼
 ┌─────────────────────┐  ┌──────────────────────┐
 │  Compliance Service │  │    Risk Service       │  MiFID II pre-trade checks:
 │                     │  │                       │  notional cap, fat-finger,
 │  Rules engine       │  └──────┬──────────┬─────┘  position limits, open orders
 │  Surveillance       │         │          │
 │  Risk scoring       │  risk_approved  risk_rejected
 │  Audit trail        │         │
 │  REST API :8010     │         ▼
 └─────────────────────┘  ┌──────────────────────┐
                           │   Matching Engine    │  Price-time priority
                           │                      │  order book, snapshots
                           └──────┬───────────────┘
                                  │
                           ┌──────┴──────────┐
                           │                 │
                           ▼                 ▼
                    trades (Kafka)  order_book_updates (Kafka)
                           │                 │
                           ▼                 ▼
                ┌──────────────────┐  ┌──────────────────────┐
                │   Trade Store    │  │  Market Data Service  │
                │                  │  │                       │
                │  PostgreSQL      │  │  Change-detected pub  │
                │  FastAPI :8000   │  │  to market_data topic │
                └──────────────────┘  └──────────────────────┘
```

**Message flow:** Client drops a FIX file → FIX Gateway parses and publishes to `raw_orders` → Order Service validates and enriches → Risk Service applies four MiFID II pre-trade checks → approved orders flow to Matching Engine via `risk_approved_orders` → matched trades fan out to Trade Store (persistence) and Market Data Service (real-time snapshot) in parallel. Rejected orders are published to `risk_rejected_orders`.

**Compliance observer:** The Compliance Service taps both `raw_orders` and `validated_orders` as a passive consumer. It applies configurable compliance rules and surveillance detections, persists violations and audit trail records to PostgreSQL, and exposes findings via a dedicated REST API.

---

## Key Features

- **FIX Protocol Ingestion** - Parses `tag=value` pipe-delimited FIX messages. Identifies Logon (`35=A`), Heartbeat (`35=0`), and NewOrderSingle (`35=D`) message types. Per-client session state is created on Logon and removed on TCP disconnect - the `fix_sessions_active` Gauge reflects the true number of live sessions at any point.
- **Event-Driven Pipeline** - Fully decoupled services communicating exclusively through Redpanda (Kafka-compatible) topics. No direct service-to-service calls.
- **Price-Time Priority Matching Engine** - Stateful in-memory order book. BUY orders match against the best ask; SELL orders match against the best bid. Partial fills and remainder queuing supported.
- **Change-Detected Market Data Publishing** - Market data snapshots are only published when bid, ask, or last trade price actually changes - no unnecessary events.
- **Trade Persistence + REST API** - Every matched trade is persisted to PostgreSQL via a Kafka consumer. A FastAPI service exposes `GET /trades`, `GET /trades/{id}`, and `GET /health` with Swagger UI.
- **Shared Internal Platform Library** - Cross-service Pydantic v2 schemas, Kafka client factory, structured JSON logging, SQLAlchemy session management, and typed exceptions - installed as an editable package across all services.
- **Compliance & Surveillance Module** - A dedicated RegTech microservice that passively observes the order pipeline. Six configurable compliance rules (missing client ID, market hours, trade size, price deviation, duplicate detection, invalid symbol) and four surveillance detections (wash trading, rapid-fire bursts, volume spikes, repeated orders) run against every order. Violations are persisted with SHA-256 tamper-evident audit trail records and are queryable via a REST API with per-client risk scores.
- **Dead Letter Queue** - FIX messages that fail parsing or validation in the filedrop client are published to a `dead_letter_orders` Kafka topic with the raw line and error reason before the file moves to `rejected/`. Failures are replayable and alertable without manual log inspection.
- **Kubernetes + Helm Deployment** - Raw manifests (`k8s/`) and a parameterised Helm chart (`helm/fixflux/`) ship alongside the Docker Compose stack. One command deploys the full pipeline to any Kubernetes cluster. The matching engine has a HorizontalPodAutoscaler; compliance policies are mounted from a ConfigMap so rules can be updated without rebuilding the image.
- **MiFID II Pre-Trade Risk Checks** - A dedicated risk-service sits between `order-service` and `matching-engine` and enforces four checks in sequence: notional cap (`price × qty > 1M`), fat-finger guard (>10% deviation from last trade price), gross/net position limits (10,000 / 5,000 units), and max open orders per client (10). All thresholds are overridable via environment variables. Rejected orders are published to `risk_rejected_orders` with a machine-readable reason; approved orders proceed to `risk_approved_orders`.
- **Four-Layer Testing** - Unit tests (pytest), component BDD tests (behave + Gherkin), infrastructure integration tests (Kafka pipeline + PostgreSQL persistence), and end-to-end BDD tests that exercise the full flow from FIX file drop to `GET /trades`.
- **Eight Independent CI/CD Pipelines** - Seven per-service pipelines (test, lint, Docker build) triggered on push and daily schedule, plus a dedicated E2E pipeline that starts the full Docker stack and runs the end-to-end BDD suite.

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

Each of the six services has an independent GitHub Actions workflow. Pipelines are triggered on:

- **Push** - path-filtered per service (only the affected service's pipeline runs)
- **Pull request** - same path filtering, enforced on every PR
- **Scheduled** - daily at 06:00 UTC to catch dependency drift and upstream regressions
- **Manual dispatch** - via the GitHub Actions tab

Each pipeline runs four stages in sequence:

```
Checkout → Install dependencies → Run pytest (coverage) → Lint → Build Docker image
```

**Coverage gate** - all pipelines enforce a minimum of 85% total coverage via `--cov-fail-under=85`. Dropping below this threshold fails the build.

**Lint stage** runs four checks in sequence - any failure blocks the build:

```bash
python -m ruff check .          # fast linting
python -m black --check .       # formatting
python -m isort --check-only .  # import ordering
python -m mypy src/             # type checking
```

All four tools read their configuration from each service's `pyproject.toml` (`[tool.ruff]`, `[tool.black]`, `[tool.isort]`, `[tool.mypy]`). Running any tool locally produces identical results to CI - no hidden CLI flags.

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

### Continuous Deployment (`deploy.yml`)

A dedicated deployment workflow fires automatically on every push to `main` that touches any file under `fixflux/`. It SSHs into the DigitalOcean Droplet and performs a zero-downtime rolling update:

```
push to main (fixflux/** path filter)
  └─ git pull origin main          # fetch latest code onto Droplet
  └─ docker compose build          # rebuild only changed layers (Docker cache)
  └─ docker compose up -d          # recreate containers with new images; new
  │                                #   services (e.g. Tempo) start alongside existing ones
  └─ curl health check             # wait up to 60 s for trade-store /health
```

**Profiles used:** `--profile full --profile monitoring` - the full trading pipeline plus Prometheus, Grafana, and Tempo are all included in every deploy.

**What makes it safe:**
- `up -d` only recreates containers whose image changed - unaffected services stay running
- PostgreSQL and Redpanda data volumes are never touched
- The health check step fails the workflow if the stack doesn't come up within 60 s, making the failure visible in GitHub Actions before anyone notices in production
- Path filter (`paths: fixflux/**`) means a README-only commit or a change to another project in the monorepo does not trigger a Droplet restart

**Required GitHub secrets:** `DO_SSH_KEY` (private key content) and `DO_DROPLET_IP` - set once in repository Settings → Secrets → Actions.

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
fixflux/
├── docker-compose.yml               # Full-stack orchestration with health-check startup ordering
├── services/
│   ├── fix-gateway/                 # FIX TCP/file ingestion, session management
│   │   ├── src/fix_gateway/
│   │   │   ├── server.py            # TCP socket server
│   │   │   ├── fix_handler.py       # FIX parser (tag=value)
│   │   │   └── session_manager.py   # Per-client session state (inc/dec on connect/disconnect)
│   │   └── tests/                   # unit + BDD tests
│   ├── order-service/               # Validation, enrichment, UUID assignment
│   ├── risk-service/                # MiFID II pre-trade risk checks (notional cap, fat-finger, position limits)
│   ├── matching-engine/             # Price-time priority order book + trade execution
│   ├── market-data-service/         # Change-detected snapshot publishing
│   ├── trade-store/                 # Kafka consumer + PostgreSQL + FastAPI REST
│   └── compliance-service/          # RegTech compliance & surveillance module
│       ├── src/compliance_service/
│       │   ├── consumer.py          # Dual-topic consumer (raw_orders + validated_orders)
│       │   ├── models.py            # SQLAlchemy: violations, risk scores, audit trail
│       │   ├── config.py            # YAML policy loader
│       │   ├── rules/
│       │   │   ├── base.py          # Rule ABC, Violation dataclass, Severity enum
│       │   │   ├── compliance/      # 6 compliance rules (size, symbol, hours, ...)
│       │   │   └── surveillance/    # 4 surveillance detections (wash, rapid-fire, ...)
│       │   ├── engine/
│       │   │   ├── rules_engine.py  # Evaluates rules, collects violations
│       │   │   ├── risk_scorer.py   # Weighted risk score per severity
│       │   │   └── audit_logger.py  # SHA-256 tamper-evident audit trail
│       │   ├── repository/          # ViolationRepository, AuditRepository
│       │   └── api/                 # FastAPI: /violations, /risk, /audit, /health
│       ├── policies/
│       │   └── compliance_policies.yaml  # All rule thresholds - no code change needed
│       └── tests/                   # unit + BDD tests
├── shared/                          # Internal platform library
│   ├── schemas/                     # Pydantic v2 event schemas (OrderEvent, TradeEvent, BookEvent)
│   ├── infrastructure/              # Kafka client factory, SQLAlchemy session, DB setup
│   ├── observability/               # Structured logging + Prometheus metric definitions
│   └── exceptions/                  # Typed exception hierarchy
├── infrastructure/
│   └── monitoring/
│       ├── prometheus.yml           # Scrape config (fix-gateway, matching-engine, trade-store)
│       ├── loki-config.yaml         # Loki log aggregation backend
│       ├── promtail-config.yaml     # Promtail log collector (Docker socket, regex pipeline)
│       ├── tempo.yaml               # Tempo distributed tracing backend
│       └── grafana/
│           ├── provisioning/
│           │   ├── datasources/     # Auto-provisioned: Prometheus, Loki, Tempo
│           │   └── dashboards/      # Dashboard provider config
│           └── dashboards/
│               └── fix_simulator_overview.json  # 15-panel trading overview (4 rows)
├── clients/
│   └── fix-filedrop-client/         # Directory watcher - drops FIX files into pipeline
├── data/                            # Sample + compliance test FIX files
├── k8s/                             # Raw Kubernetes manifests (apply with kubectl or kustomize)
│   ├── 00-namespace.yaml
│   ├── 01-configmap.yaml
│   ├── 02-secret.yaml
│   ├── redpanda.yaml                # StatefulSet + headless + ClusterIP services
│   ├── postgres.yaml                # StatefulSet + PVC
│   ├── fix-gateway.yaml             # Deployment + Service
│   ├── matching-engine.yaml         # Deployment + Service + HPA
│   ├── trade-store.yaml             # API Deployment + consumer Deployment + LoadBalancer
│   ├── compliance-service.yaml      # API Deployment + consumer Deployment + LoadBalancer + policies ConfigMap
│   ├── market-data-service.yaml
│   └── kustomization.yaml           # Apply everything: kubectl apply -k k8s/
├── helm/
│   └── fixflux/                     # Helm chart - parameterised for dev/staging/prod
│       ├── Chart.yaml
│       ├── values.yaml              # All tuneable knobs (replicas, resources, image registry)
│       └── templates/               # Go-templated versions of all k8s/ manifests
├── tests/
│   └── integration/                 # BDD integration tests (PostgreSQL + Kafka required)
│       ├── environment.py           # Behave hooks: DB truncation, Kafka consumer init
│       ├── features/
│       │   ├── filedrop_e2e_pipeline.feature      # Full E2E: filedrop → risk → match → REST
│       │   ├── risk_pipeline_integration.feature  # Risk service: notional, fat-finger, limits
│       │   ├── kafka_trade_pipeline.feature       # Kafka → trade-store persistence
│       │   ├── trade_persistence.feature          # Trade Store REST API + DB assertions
│       │   └── chaos_recovery.feature             # Service kill + recovery scenarios
│       └── steps/                   # Step definitions: filedrop, risk, kafka, chaos, trade
└── scripts/
    ├── update_status_badge.py       # Queries Prometheus; updates live status badge in README
    ├── check-observability.sh       # Smoke-tests the full monitoring stack on the Droplet
    ├── clear_db.py                  # Truncates all tables (dev reset)
    ├── test_db_connection.py        # Verifies PostgreSQL connectivity
    └── k8s-*.ps1 / build-images.ps1 # Kubernetes + Docker convenience scripts (Windows)
```

---

## Services Reference

| Service | Consumes | Produces | Responsibility |
|---|---|---|---|
| **fix-gateway** | - | `raw_orders`, `dead_letter_orders` | Parses FIX `tag=value` messages, identifies message types, manages per-client sessions; publishes rejected lines to dead letter topic |
| **order-service** | `raw_orders` | `validated_orders` | Validates price/quantity/side rules, assigns UUID order ID, drops invalid orders |
| **risk-service** | `validated_orders`, `trades` | `risk_approved_orders`, `risk_rejected_orders` | Four MiFID II pre-trade checks: notional cap, fat-finger, gross/net position limits, max open orders; tracks positions from `trades` topic |
| **matching-engine** | `risk_approved_orders` | `trades`, `order_book_updates` | Price-time priority matching, partial fills, order book snapshots on each match |
| **market-data-service** | `trades`, `order_book_updates` | `market_data` | Caches best bid/ask/last trade; publishes snapshot only on change |
| **trade-store** | `trades` | - | Persists trades to PostgreSQL; exposes REST API via FastAPI |
| **compliance-service** | `raw_orders`, `validated_orders` | - (DB only) | Passive observer: applies compliance rules + surveillance detections; persists violations, risk scores, and audit trail; exposes REST API |
| **shared** | - | - | Internal library: schemas, Kafka factory, logging, DB session, exceptions |

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 24+ (includes Docker Compose v2)
- Python 3.11+ (for the local file-drop watcher only)

### 1. Clone

```bash
git clone https://github.com/NEMETOM/python-engineering-lab.git
cd python-engineering-lab/fixflux
```

### 2. Start the stack

Services are grouped into profiles:

| Profile | Services |
|---|---|
| _(none)_ | `redpanda`, `postgres` only |
| `pipeline` | + `fix-gateway`, `order-service`, `matching-engine`, `trade-store`, `compliance-api`, `compliance-consumer` |
| `full` | + all of the above + `market-data-service` |
| `monitoring` | + `prometheus`, `grafana`, `tempo` (combine with pipeline or full) |

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
| compliance-api | Up | 8010 |
| compliance-consumer | Up | - |
| prometheus | Up (monitoring profile) | 9090 |
| grafana | Up (monitoring profile) | 3000 |
| tempo | Up (monitoring profile) | 3200 (query), 4318 (OTLP) |

### 4. Trade Store REST API

Swagger UI: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/trades` | All trades (optional `?symbol=EURUSD`) |
| `GET` | `/trades/{trade_id}` | Single trade by ID |

> Only matched trades appear in the API. Unmatched orders rest in the matching engine's in-memory order book until a crossing counterpart arrives.

### 5. Compliance REST API

Swagger UI: `http://localhost:8010/docs`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/violations` | List violations (filter: `client_id`, `severity`, `status`, `rule_name`) |
| `GET` | `/violations/{id}` | Single violation detail with raw event payload |
| `PATCH` | `/violations/{id}/status` | Update status: `REVIEWED`, `DISMISSED`, `ESCALATED` |
| `GET` | `/risk` | All clients sorted by risk score descending |
| `GET` | `/risk/{client_id}` | Risk profile for a specific client |
| `GET` | `/audit` | Compliance audit trail (filter: `client_id`, `event_type`) |

Compliance policies (enabled/disabled rules, thresholds) are configured in `services/compliance-service/policies/compliance_policies.yaml` - no code change required.

### 6. Run the file-drop watcher (separate terminal)

```bash
pip install -e shared
pip install -e services/fix-gateway

python clients/fix-filedrop-client/watcher.py
```

### 7. Drop a FIX order file

```bash
# Create a buy order
echo "35=D|55=EURUSD|54=1|44=1.09|38=100|" > clients/fix-filedrop-client/filedrop/buy_001.txt

# Create a matching sell order
echo "35=D|55=EURUSD|54=2|44=1.09|38=100|" > clients/fix-filedrop-client/filedrop/sell_001.txt
```

The watcher detects each file, publishes to `raw_orders`, and moves it to `processed/` on success or `rejected/` on validation failure. Ready-to-use sample files are in `data/`.

**Compliance test data** - the `data/` directory includes files purpose-built to exercise the compliance rules engine:

| File | What it triggers |
|---|---|
| `compliance_valid_orders.txt` | All rules pass - clean baseline |
| `compliance_missing_client_id.txt` | `MissingClientIdRule` HIGH |
| `compliance_invalid_symbol.txt` | `InvalidSymbolRule` CRITICAL |
| `compliance_excessive_size.txt` | `TradeSizeRule` HIGH (per-symbol limits) |
| `compliance_price_deviation.txt` | `PriceDeviationRule` HIGH (builds baseline, then spikes) |
| `compliance_duplicate_orders.txt` | `DuplicateOrderRule` MEDIUM |
| `surveillance_wash_trading.txt` | `WashTradingRule` CRITICAL |
| `surveillance_rapid_fire.txt` | `RapidFireRule` HIGH |
| `surveillance_volume_spike.txt` | `VolumeSpikeRule` HIGH |
| `surveillance_repeated_orders.txt` | `RepeatedOrdersRule` MEDIUM |

---

## Kubernetes Deployment

The project ships with both raw manifests (`k8s/`) and a Helm chart (`helm/fixflux/`) for Kubernetes deployment. All services are already Kubernetes-ready - they use environment variables for all configuration and have no local-filesystem state.

**Quick reference - most common commands:**

- Enable a local cluster: Docker Desktop → Settings → Kubernetes → Enable Kubernetes
- Deploy everything: `kubectl apply -k k8s/`
- Deploy with Helm: `helm install fix-simulator ./helm/fixflux --namespace fix-simulator --create-namespace`
- Watch pods come up: `kubectl get pods -n fix-simulator -w`
- Stream logs: `kubectl logs -n fix-simulator deploy/compliance-api -f`
- Access APIs locally: `kubectl port-forward -n fix-simulator svc/trade-store 8000:8000`
- Update compliance rules without rebuilding: `kubectl edit configmap -n fix-simulator compliance-policies`
- Tear down: `kubectl delete -k k8s/` or `helm uninstall fix-simulator -n fix-simulator`

See [§ Day-to-day operations](#4-day-to-day-operations) below for the full operations reference.

### Prerequisites

- Kubernetes cluster (local: [minikube](https://minikube.sigs.k8s.io/) or [kind](https://kind.sigs.k8s.io/), cloud: EKS / GKE / AKS)
- `kubectl` configured against your cluster
- `helm` v3+ (for the Helm chart option)
- `metrics-server` installed in the cluster (required for HPA on the matching engine)

### 1. Build and push images

```bash
cd fixflux

# Build all service images
docker build -f services/fix-gateway/Dockerfile        -t YOUR_REGISTRY/fix-gateway:latest        .
docker build -f services/order-service/Dockerfile      -t YOUR_REGISTRY/order-service:latest      .
docker build -f services/matching-engine/Dockerfile    -t YOUR_REGISTRY/matching-engine:latest    .
docker build -f services/trade-store/Dockerfile        -t YOUR_REGISTRY/trade-store:latest        .
docker build -f services/compliance-service/Dockerfile -t YOUR_REGISTRY/compliance-service:latest .
docker build -f services/market-data-service/Dockerfile -t YOUR_REGISTRY/market-data-service:latest .

# Push to your registry
docker push YOUR_REGISTRY/fix-gateway:latest
# ... repeat for each service
```

> For local testing with minikube, run `eval $(minikube docker-env)` before building so images land directly in the cluster's registry without a push step.

### 2a. Deploy with kubectl (raw manifests)

```bash
# Update the secret in k8s/02-secret.yaml with real credentials first, then:
kubectl apply -k k8s/

# Watch pods come up
kubectl get pods -n fix-simulator -w
```

Apply order is handled automatically by kustomize. Redpanda and PostgreSQL must be `Running` and passing their health probes before the application pods schedule successfully (Kubernetes restarts them automatically until the dependency is ready).

### 2b. Deploy with Helm

```bash
# Install with default values (uses image tag 'latest', no registry prefix)
helm install fix-simulator ./helm/fixflux \
  --namespace fix-simulator --create-namespace

# Install with a custom image registry and production-grade resource limits
helm install fix-simulator ./helm/fixflux \
  --namespace fix-simulator --create-namespace \
  --set image.registry=docker.io/myuser \
  --set image.tag=1.0.0 \
  --set matchingEngine.autoscaling.maxReplicas=10 \
  --set postgres.credentials.password=supersecret

# Upgrade after a code change
helm upgrade fix-simulator ./helm/fixflux --namespace fix-simulator --set image.tag=1.0.1

# Tear down
helm uninstall fix-simulator --namespace fix-simulator
```

**What a single `helm install` provisions**

| Component | Kubernetes resource | Notes |
|---|---|---|
| `redpanda` | StatefulSet + headless Service | Kafka-compatible broker, no JVM or Zookeeper |
| `postgres` | StatefulSet + PersistentVolumeClaim | Durable trade and violation storage |
| `fix-gateway` | Deployment + Service | FIX ingestion, TCP port 9878 |
| `order-service` | Deployment | Validation + enrichment, Kafka consumer |
| `risk-service` | Deployment | MiFID II pre-trade checks |
| `matching-engine` | Deployment + HPA | Price-time priority matching; autoscales 1-5 replicas at 70% CPU |
| `trade-store` | 2x Deployment + LoadBalancer | REST API (port 8000) + Kafka consumer, independently scalable |
| `compliance-service` | 2x Deployment + LoadBalancer + ConfigMap | REST API (port 8010) + observer; compliance rules mounted from ConfigMap |
| `market-data-service` | Deployment | Change-detected snapshot publisher |

**Key `values.yaml` knobs**

| Key | Default | What it controls |
|---|---|---|
| `image.registry` | _(none)_ | Docker registry prefix (e.g. `registry.digitalocean.com/fixflux`) |
| `image.tag` | `latest` | Image tag applied to all deployments |
| `matchingEngine.autoscaling.maxReplicas` | `5` | HPA upper bound on the matching engine |
| `postgres.credentials.password` | `fixpass` | PostgreSQL password - always override in production |
| `resources.requests.cpu` | `100m` | Per-pod CPU request |
| `resources.limits.memory` | `256Mi` | Per-pod memory ceiling |

Override any value inline with `--set key=value` or supply an environment-specific values file:

```bash
# Production deploy targeting DigitalOcean Container Registry
helm install fixflux ./helm/fixflux \
  --namespace fixflux --create-namespace \
  --values helm/values-digitalocean.yaml \
  --set image.tag=$(git rev-parse --short HEAD)
```

`helm/values-digitalocean.yaml` overrides the registry URL, storage class, and resource limits for the DigitalOcean environment. See `CLOUD_TRANSITION_PLAN.md` for the full production deployment checklist.

### 3. Verify

```bash
kubectl get all -n fix-simulator
```

| Resource | Expected state |
|---|---|
| `statefulset/redpanda` | 1/1 Ready |
| `statefulset/postgres` | 1/1 Ready |
| `deployment/fix-gateway` | 1/1 Available |
| `deployment/order-service` | 1/1 Available |
| `deployment/matching-engine` | 1/1+ Available (HPA manages replicas) |
| `deployment/trade-store-api` | 2/2 Available |
| `deployment/trade-store-consumer` | 1/1 Available |
| `deployment/compliance-api` | 1/1 Available |
| `deployment/compliance-consumer` | 1/1 Available |
| `deployment/market-data-service` | 1/1 Available |

```bash
# Get the external IPs for the two REST APIs
kubectl get svc -n fix-simulator trade-store compliance-service

# Trade Store API
curl http://<TRADE_STORE_EXTERNAL_IP>:8000/health

# Compliance API
curl http://<COMPLIANCE_EXTERNAL_IP>:8010/health
```

### 4. Day-to-day operations

**View logs**

```bash
# Stream logs from any service
kubectl logs -n fix-simulator deploy/matching-engine -f
kubectl logs -n fix-simulator deploy/compliance-api -f
kubectl logs -n fix-simulator deploy/trade-store-consumer -f

# Last 100 lines from all pods of a deployment
kubectl logs -n fix-simulator deploy/compliance-consumer --tail=100
```

**Access the APIs locally** (when no external LoadBalancer is available, e.g. minikube)

```bash
# Forward Trade Store API to localhost:8000
kubectl port-forward -n fix-simulator svc/trade-store 8000:8000 &

# Forward Compliance API to localhost:8010
kubectl port-forward -n fix-simulator svc/compliance-service 8010:8010 &

# Now query as normal
curl http://localhost:8000/trades
curl http://localhost:8010/violations
curl http://localhost:8010/risk
```

**Send a test order through the pipeline**

```bash
# Port-forward the FIX gateway TCP socket
kubectl port-forward -n fix-simulator svc/fix-gateway 9878:9878 &

# Drop a compliance test file via the filedrop client (runs locally)
cp data/compliance_excessive_size.txt clients/fix-filedrop-client/filedrop/

# Then check violations appeared
curl http://localhost:8010/violations | python -m json.tool
```

**Scale a service manually**

```bash
# Scale trade-store API to 3 replicas
kubectl scale -n fix-simulator deploy/trade-store-api --replicas=3

# Check HPA status on the matching engine
kubectl get hpa -n fix-simulator matching-engine

# Override HPA and force a specific replica count (disables autoscaling temporarily)
kubectl patch hpa -n fix-simulator matching-engine -p '{"spec":{"minReplicas":2,"maxReplicas":2}}'
```

**Update compliance policies without rebuilding**

```bash
# Edit rules live - changes take effect on the next consumer poll cycle
kubectl edit configmap -n fix-simulator compliance-policies

# Or apply an updated policies file
kubectl create configmap compliance-policies \
  --from-file=compliance_policies.yaml=services/compliance-service/policies/compliance_policies.yaml \
  --namespace fix-simulator --dry-run=client -o yaml | kubectl apply -f -

# Restart consumers to pick up the new mount
kubectl rollout restart -n fix-simulator deploy/compliance-consumer
kubectl rollout restart -n fix-simulator deploy/compliance-api
```

**Rolling restart after a new image**

```bash
# Restart a single service (zero-downtime for replicas > 1)
kubectl rollout restart -n fix-simulator deploy/trade-store-api

# Watch the rollout
kubectl rollout status -n fix-simulator deploy/trade-store-api

# Roll back if something goes wrong
kubectl rollout undo -n fix-simulator deploy/trade-store-api
```

**Tear down**

```bash
# kubectl
kubectl delete -k k8s/

# Helm
helm uninstall fix-simulator --namespace fix-simulator
kubectl delete namespace fix-simulator   # also removes PVCs and all remaining resources
```

### Architecture notes

- **Redpanda** runs as a `StatefulSet` with a headless service for pod identity and a standard `ClusterIP` service (`redpanda:9092`) for Kafka clients. All application services use `KAFKA_BROKER=redpanda:9092`.
- **Compliance policies** are mounted from a `ConfigMap` (`compliance-policies`) so rules can be updated with `kubectl edit configmap compliance-policies -n fix-simulator` without rebuilding the image.
- **HPA** on the matching engine scales between 1 and 5 replicas at 70% CPU. Requires `metrics-server` in the cluster.
- **Secrets** - `k8s/02-secret.yaml` uses `stringData` for readability during development. For production, use `kubectl create secret` with values from a secrets manager (AWS Secrets Manager, Vault, etc.) and never commit credentials to the repository.

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
cd services/matching-engine    && python -m pytest -v
cd services/order-service      && python -m pytest -v
cd services/risk-service       && python -m pytest -v
cd services/trade-store        && python -m pytest -v
cd services/market-data-service && python -m pytest -v
cd services/fix-gateway        && python -m pytest -v
cd services/compliance-service && python -m pytest -v
cd shared                      && python -m pytest -v
```

### BDD Component Tests (Gherkin)

Business behaviour is specified as Gherkin feature files and executed with behave. Feature files and step implementations are co-located under `tests/bdd/` in each service.

```bash
cd services/matching-engine    && python -m behave tests/bdd/features/
cd services/order-service      && python -m behave tests/bdd/features/
cd services/risk-service       && python -m behave tests/bdd/features/
cd services/trade-store        && python -m behave tests/bdd/features/
cd services/market-data-service && python -m behave tests/bdd/features/
cd services/compliance-service && python -m behave tests/bdd/features/
```

The risk-service BDD suite covers three feature files:

| Feature | Scenarios |
|---|---|
| `risk_checks.feature` | Notional cap approved/rejected, fat-finger approved/rejected/skipped (no ref price) |
| `position_limits.feature` | Gross/net position approved/rejected, max open orders, fills release slots |
| `risk_pipeline.feature` | Approved orders forwarded, rejected orders sent to rejected topic, trades update last price |

The compliance BDD suite covers two feature files:

| Feature | Scenarios |
|---|---|
| `compliance_rules.feature` | Missing client ID, trade size limits, invalid symbol, duplicate detection |
| `surveillance_detections.feature` | Wash trading, rapid-fire bursts, volume spike, repeated orders |

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

### End-to-End BDD Tests

The E2E suite (`@e2e`) exercises the complete pipeline: a FIX file is dropped into the filedrop client, flows through Kafka → order-service → risk-service → matching-engine → trade-store, and the resulting trade is asserted via `GET /trades`. The full Docker stack must be running.

```bash
# Start the full pipeline
docker compose --profile full up -d

# Install test dependencies (once)
pip install -e shared && pip install -e services/fix-gateway && pip install -e services/trade-store
pip install behave kafka-python httpx sqlalchemy psycopg2-binary

# Run the full E2E suite (pretty output + step timings configured in behave.ini)
cd tests/integration
python -m behave features/filedrop_e2e_pipeline.feature --tags="@e2e" --tags="~@volume"

# Run the golden path only (fastest demo of the core flow)
python -m behave features/filedrop_e2e_pipeline.feature --tags="@golden-path"

# Run the volume test (manual - takes up to 4 minutes)
python -m behave features/filedrop_e2e_pipeline.feature --tags="@volume"
```

Six scenarios are covered across five distinct pipeline behaviours:

| Tag | Scenario | What it verifies |
|---|---|---|
| `@golden-path` | A buy and sell order cross - trade flows end-to-end and appears via REST | Happy path: one crossing pair produces a matched trade visible in `GET /trades` within 30 s |
| _(none)_ | A malformed FIX message is quarantined without blocking valid orders | Resilience: a bad FIX line goes to the dead-letter topic; subsequent valid orders are unaffected |
| `@needs_risk_service` | An oversized order is blocked by the MiFID II notional cap | Risk gate: `price × qty > 1,000,000` is rejected before matching; no trade is produced |
| _(none)_ | An order breaching the per-symbol size limit triggers a compliance violation | Compliance observer: `TradeSizeRule` flags the order in `GET /violations` within 20 s |
| _(none)_ | Opposing orders from the same client trigger wash trading surveillance | Surveillance: `WashTradingRule` fires when the same client submits both sides within the 300 s window |
| `@volume` | The pipeline processes high-volume order flow without message loss | Throughput: 1,000 crossing pairs all matched and persisted within 120 s |

**Output format** - `behave.ini` configures `pretty` format with step timings (`show_timings = true`) and no source file references (`show_source = false`), giving clean, audience-friendly output during demos.

In CI, the E2E workflow (`e2e.yml`) runs as two separate jobs:

| Job | Trigger | Tag filter | Purpose |
|---|---|---|---|
| `e2e` | Weekly schedule (Mon 07:00 UTC) + manual dispatch | `@e2e` excluding `@volume` | Correctness - fast, runs on every scheduled and manual trigger |
| `volume` | Manual dispatch only | `@volume` | Throughput proof - skipped on the weekly schedule to avoid flaky long-running failures on shared CI runners |

---

## Environment Variables

| Variable | Default | Used by |
|---|---|---|
| `KAFKA_BROKER` | `localhost:9092` | All services |
| `DATABASE_URL` | _(reads config.yaml)_ | trade-store, compliance-service |
| `LOG_LEVEL` | `INFO` | All services |
| `LOG_FORMAT` | `plain` | All services (`json` for structured logs) |
| `PUBLISH_INTERVAL` | `10` | market-data-service |
| `RISK_NOTIONAL_LIMIT` | `1000000` | risk-service - rejects if `price × qty` exceeds this |
| `RISK_FAT_FINGER_PCT` | `10.0` | risk-service - rejects if order price deviates >N% from last trade |
| `RISK_GROSS_POSITION_LIMIT` | `10000` | risk-service - max absolute position per client per symbol |
| `RISK_NET_POSITION_LIMIT` | `5000` | risk-service - max net long or short per client per symbol |
| `RISK_MAX_OPEN_ORDERS` | `10` | risk-service - max unmatched open orders per client |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | _(unset)_ | order-service, risk-service, matching-engine, trade-store-consumer - traces exported to Tempo when set; spans dropped silently when unset |

---

## Monitoring & Observability

The simulator ships with a full three-pillar observability stack (metrics, logs, traces), reflecting production observability practice in trading systems.

### Stack

| Component | Role |
|---|---|
| **Prometheus** `v2.51` | Scrapes metrics from each service every 15 s; retains time-series data |
| **Grafana** `v10.4` | Pre-provisioned dashboard with 4 collapsible rows and 15 panels; also the UI for traces and logs via Explore |
| **Tempo** `v2.4` | Distributed trace backend; receives OTLP spans from all services, queryable via Grafana Explore |
| **Loki** `v2.9` | Log aggregation backend; stores log streams indexed by container and log level |
| **Promtail** `v2.9` | Log collector; reads Docker container stdout via the Docker socket and ships to Loki; parses the `TIMESTAMP \| LEVEL \| module \| message` format into labels |
| **prometheus-client** `>=0.20` | Python library; embedded HTTP server (fix-gateway, matching-engine) and ASGI endpoint (trade-store) |
| **OpenTelemetry SDK** `>=1.24` | Instruments each Kafka consumer; propagates trace context as `_trace_id`/`_span_id` fields through Kafka message payloads |

### Monitoring Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           Docker Network                             │
│                                                                      │
│  fix-gateway:8001/metrics  ──────────┐                               │
│  matching-engine:8003/metrics ───────┼──► Prometheus:9090 ────────┐ │
│  trade-store:8000/metrics ───────────┘                             │ │
│                                                                    ▼ │
│  order-service ──────────────────────┐                       Grafana:3000
│  risk-service  ──────────────────────┤                            ▲ │
│  matching-engine ────────────────────┼──► Tempo:4318 (OTLP) ──────┤ │
│  trade-store-consumer ───────────────┘       :3200 (query)        │ │
│                                                                    │ │
│  all services (stdout) ──► Promtail ──► Loki:3100 ────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

**Metrics path:** Prometheus scrapes fix-gateway, matching-engine, and trade-store every 15 s. Grafana reads Prometheus as its primary datasource (auto-provisioned).

**Traces path:** Each of the four pipeline consumers emits OpenTelemetry spans to Tempo via OTLP HTTP (`port 4318`). Grafana's Tempo datasource (auto-provisioned) makes traces queryable from Explore.

**Logs path:** Promtail reads Docker container stdout via the Docker socket and ships all log streams to Loki. The pipeline stage parses the `TIMESTAMP | LEVEL | module | message` format, promoting `level` and `module` to indexed Loki labels. Grafana's Loki datasource (auto-provisioned) makes logs queryable from Explore with LogQL.

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
| Grafana Explore (logs) | `http://localhost:3000/explore` - select **Loki** datasource | admin / admin |
| Grafana Explore (traces) | `http://localhost:3000/explore` - select **Tempo** datasource | admin / admin |
| Prometheus | `http://localhost:9090` | - |
| Loki | `http://localhost:3100` | - |
| Tempo | `http://localhost:3200` | - |
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
| `orders_in_book` | Gauge | `side` (buy, sell), `symbol` | matching-engine |
| `kafka_messages_consumed_total` | Counter | `topic`, `service` | matching-engine |
| `api_requests_total` | Counter | `endpoint`, `method`, `status_code` | trade-store |
| `api_request_latency_seconds` | Histogram | `endpoint` | trade-store |

All metric definitions live in [`shared/observability/metrics.py`](shared/observability/metrics.py) - a single source of truth importable by any service via `PYTHONPATH`.

### Grafana Dashboard

The pre-provisioned dashboard (`fix_simulator_overview`) has four rows, 15 panels:

| Row | Panels |
|---|---|
| **FIX Gateway** | Messages/sec by type, Active Sessions, Parse Errors/min, Message type distribution |
| **Matching Engine** | Trades/sec by symbol, Latency P99, Latency P50, Order Book Depth (buy/sell per symbol), Cumulative Trades Matched |
| **Trade Store API** | Request rate, API Latency P99, 5xx Error Rate, Latency percentiles p50/p95/p99 |
| **Kafka Throughput** | Messages consumed/sec, Messages produced/sec |

#### Panel Descriptions

| Row | Panel | Type | What it tells you |
|---|---|---|---|
| FIX Gateway | Messages/sec by type | Time series | Throughput split by `logon`, `heartbeat`, `new_order`. A spike in `heartbeat` with no `new_order` activity means a connected but idle client. Flat line overall means no new orders are arriving. |
| FIX Gateway | Active Sessions | Stat | Count of currently live FIX TCP connections. Drops to 0 if the gateway loses its accept loop or a client disconnects without a Logon. |
| FIX Gateway | Parse Errors/min | Stat | Rate of messages that failed FIX tag=value parsing. Any non-zero value warrants investigation - valid clients do not send malformed frames. |
| FIX Gateway | Message type distribution | Donut | Cumulative share of each message type over the panel window. Useful for understanding the order-to-heartbeat ratio in a load test. |
| Matching Engine | Trades executed/sec by symbol | Time series | Matching throughput per instrument. Staircase pattern during a volume test (batch burst), flat after. Zero for a symbol means no crossing orders have arrived. |
| Matching Engine | Matching latency P99 | Gauge | 99th-percentile time from order arrival to trade event emission. Sub-millisecond in normal operation. Spikes above 10 ms suggest GIL contention or Kafka producer backpressure. |
| Matching Engine | Matching latency P50 | Gauge | Median matching latency. Divergence between P50 and P99 reveals tail-latency outliers rather than a general slowdown. |
| Matching Engine | Order Book Depth (buy/sell) | Time series | Current resting order count per side and symbol (legend: `BTCUSD buy`, `BTCUSD sell`). Non-zero sell side confirms non-crossing limit orders are queuing. Zero sell-side with a rising trade counter is expected when sells match immediately - see Cumulative Trades panel for confirmation. |
| Matching Engine | Cumulative Trades Matched | Time series | Raw `trades_executed_total` counter per symbol - monotonically rising during active matching, plateau after. Complements Order Book Depth: a flat sell line there plus a rising counter here means sells are matching immediately rather than resting in the book. |
| Trade Store API | Request rate | Time series | Inbound `GET /trades` request rate. Sustained rate indicates active consumers polling results. |
| Trade Store API | API Latency P99 | Gauge | PostgreSQL-backed read latency at the 99th percentile. Values above 100 ms typically indicate a missing index or connection pool exhaustion. |
| Trade Store API | 5xx Error Rate | Stat | Server-side errors per minute. Any non-zero value is a failure - the trade store has no expected error conditions once the database is up. |
| Trade Store API | Latency percentiles (P50/P95/P99) | Time series | Three latency quantiles on one panel. Parallel lines mean uniform latency; diverging P99 signals occasional slow queries. |
| Kafka Throughput | Messages consumed/sec | Time series | Messages read from Kafka per second, labelled by `service` and `topic`. Divergence between produced and consumed rates signals consumer lag building up. |
| Kafka Throughput | Messages produced/sec | Time series | Messages written to Kafka per second. Currently shows zero - metric is defined but no service increments it yet (see Instrumentation Gaps). |

### Dashboard Queries

The exact PromQL expressions used in each panel - useful for reuse, alerting rules, and understanding what each panel measures:

| Row | Panel | PromQL |
|---|---|---|
| **FIX Gateway** | Messages/sec by type | `rate(fix_messages_received_total[1m])` |
| **FIX Gateway** | Active sessions | `fix_sessions_active` |
| **FIX Gateway** | Parse errors/min | `rate(fix_messages_parse_errors_total[1m]) * 60` |
| **FIX Gateway** | Message type distribution | `sum by(msg_type)(increase(fix_messages_received_total[5m]))` |
| **Matching Engine** | Trades executed/sec by symbol | `rate(trades_executed_total[1m])` |
| **Matching Engine** | Matching latency P99 | `histogram_quantile(0.99, rate(order_matching_latency_seconds_bucket[5m]))` |
| **Matching Engine** | Matching latency P50 | `histogram_quantile(0.50, rate(order_matching_latency_seconds_bucket[5m]))` |
| **Matching Engine** | Order book depth (buy/sell per symbol) | `orders_in_book` (legend: `{{symbol}} {{side}}`) |
| **Matching Engine** | Cumulative trades matched | `trades_executed_total` (legend: `{{symbol}}`) |
| **Trade Store API** | Request rate | `rate(api_requests_total[1m])` |
| **Trade Store API** | API latency P99 | `histogram_quantile(0.99, rate(api_request_latency_seconds_bucket[5m]))` |
| **Trade Store API** | 5xx error rate/min | `rate(api_requests_total{status_code=~"5.."}[1m]) * 60` |
| **Trade Store API** | Latency percentiles (P50/P95/P99) | `histogram_quantile(0.50\|0.95\|0.99, rate(api_request_latency_seconds_bucket[5m]))` |
| **Kafka Throughput** | Messages consumed/sec | `rate(kafka_messages_consumed_total[1m])` |
| **Kafka Throughput** | Messages produced/sec | `rate(kafka_messages_produced_total[1m])` |

All counters use `rate()` rather than raw values so Grafana handles counter resets on pod restarts correctly. Latency panels use `histogram_quantile()` over a 5-minute window - long enough to smooth noise, short enough to catch spikes within a few scrape intervals.

### Distributed Traces

Every order flowing through the pipeline produces one distributed trace spanning four services. Trace context is propagated as `_trace_id` and `_span_id` fields injected directly into Kafka message payloads - no sidecar or agent required.

**Trace chain per order:**

```
[order-service.process]
    └─ [risk-service.validated_orders]
           └─ [matching-engine.process]
                  └─ [trade-store.persist]
```

**Span attributes:**

| Service | Span name | Attributes |
|---|---|---|
| order-service | `order-service.process` | `order.id`, `order.symbol` |
| risk-service | `risk-service.validated_orders` | `order.id`, `order.symbol`, `kafka.topic` |
| matching-engine | `matching-engine.process` | `order.id`, `order.symbol` |
| trade-store | `trade-store.persist` | `trade.id` |

**How to view traces:**

1. `docker compose --profile full --profile monitoring up -d`
2. Open `http://localhost:3000` → Explore → select **Tempo** datasource
3. Search tab → filter by `service.name = order-service`
4. Click any trace row to expand the span waterfall

**Trace-to-metrics:** The Tempo datasource is linked to Prometheus. Clicking the Prometheus icon on any span navigates directly to the corresponding `kafka_messages_consumed_total` metric for that service.

**Without monitoring profile:** Services have `OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318` set in docker-compose.yml. When Tempo is not running the `BatchSpanProcessor` drops spans silently - no error, no service impact.

### Accessing Logs

All services log to **stdout** in `TIMESTAMP | LEVEL | module | message` format. Docker captures this via its default `json-file` driver so logs are available immediately without any additional setup.

#### Log format

```
2026-07-05 10:23:44,901 | INFO  | risk_service.consumer     | pre_trade_decision | order=abc123 client=E2E_ABC symbol=BTCUSD side=BUY qty=200 price=1000.00 notional=200000.00 last_price=0.0 decision=APPROVED
2026-07-05 10:23:45,123 | INFO  | compliance_service.consumer | compliance_decision | client=E2E_ABC symbol=BTCUSD qty=200 price=1000.0 status=VIOLATIONS_DETECTED violations=1 rules=['TradeSizeRule']
2026-07-05 10:23:45,200 | WARN  | risk_service.consumer     | pre_trade_decision | order=def456 client=E2E_XYZ symbol=AAPL side=BUY qty=6000 price=175.00 notional=1050000.00 last_price=175.0 decision=REJECTED reason='notional 1050000.00 exceeds limit 1000000.00'
```

The two structured decision log events:

| Keyword | Service | Level | When emitted |
|---|---|---|---|
| `pre_trade_decision` | risk-service | INFO (approved) / WARN (rejected) | Once per order, after all pre-trade checks complete |
| `compliance_decision` | compliance-service | INFO | Once per order, after all compliance rules evaluated |

#### Docker Compose (local or Droplet)

```bash
# Stream logs from all services live
docker compose logs -f

# Stream logs from specific services only
docker compose logs -f risk-service compliance-service

# All pre-trade decisions (live)
docker compose logs -f risk-service | grep pre_trade_decision

# All compliance decisions (live)
docker compose logs -f compliance-service | grep compliance_decision

# Only rejections
docker compose logs risk-service | grep "decision=REJECTED"

# All violations detected (non-compliant orders)
docker compose logs compliance-service | grep "status=VIOLATIONS_DETECTED"

# Specific rule triggered
docker compose logs compliance-service | grep "TradeSizeRule"

# Trace a single order by ID across both services
docker compose logs risk-service compliance-service | grep "order=<order_id>"

# Save to file for offline analysis
docker compose logs --no-log-prefix risk-service > risk_decisions.log
```

#### Remote access on a Digital Ocean Droplet

SSH into the Droplet, then use the same `docker compose logs` commands above. To follow logs without keeping the SSH session open:

```bash
# Write to a rotating file on the Droplet (runs in background)
docker compose logs -f risk-service compliance-service >> /var/log/fixflux-decisions.log &

# Or use tmux to keep a live tail session persistent across SSH disconnects
tmux new-session -d -s logs "docker compose logs -f risk-service compliance-service"
tmux attach -t logs   # reconnect later
```

Docker's `json-file` log files are stored on the host at `/var/lib/docker/containers/<container-id>/<container-id>-json.log`. They persist across container restarts but are cleared on `docker compose down -v`.

#### Loki + Grafana (included in monitoring profile)

Loki and Promtail are part of the `monitoring` profile. When the monitoring stack is up, logs from all containers are automatically collected and queryable from Grafana Explore - no extra steps needed.

**Open Grafana Explore → select Loki datasource**, then use LogQL:

```logql
# All pre-trade decisions
{container=~".*risk-service.*"} |= "pre_trade_decision"

# Only rejections
{container=~".*risk-service.*"} | level="WARNING" |= "decision=REJECTED"

# Compliance violations for a specific rule
{container=~".*compliance-consumer.*"} |= "VIOLATIONS_DETECTED" |= "TradeSizeRule"

# Trace a single order across both services
{container=~".*(risk-service|compliance-consumer).*"} |= "order=<order_id>"

# All WARNING or ERROR level logs across all services
{logstream="stderr"} | level=~"WARNING|ERROR"
```

Promtail parses the `TIMESTAMP | LEVEL | module | message` log format and promotes `level` and `module` to indexed Loki labels, so label-based filtering (`level="WARNING"`) is fast (index lookup) while content filtering (`|= "TradeSizeRule"`) does a line scan.

**Windows / Docker Desktop note:** Promtail uses the Docker socket (`/var/run/docker.sock`) to read logs. This works on the Droplet (Linux) and on Docker Desktop for Windows/Mac. If Promtail fails to start locally, verify Docker Desktop has the socket enabled under Settings → Advanced → "Allow the default Docker socket to be used".

### Instrumentation Gaps

Honest coverage status - metrics defined in `shared/observability/metrics.py` but not yet wired up, and services with no instrumentation at all:

| Service / Metric | Status | Notes |
|---|---|---|
| `fix-gateway` | Fully instrumented | 4 metrics: sessions, message counts, parse errors, reconnects |
| `matching-engine` | Fully instrumented | 3 metrics: trades, latency histogram, order book depth |
| `trade-store` | Partially instrumented | API layer covered via middleware; `trades_stored_total` Counter defined but never called in the consumer |
| `order-service` | Not instrumented | `orders_processed_total{status}` Counter defined in shared but never incremented |
| `market-data-service` | Not instrumented | No metrics calls anywhere in the service |
| `compliance-service` | Not instrumented | No custom metrics; violations/risk scores are only queryable via REST |
| `kafka_messages_produced_total` | Defined, unused | Defined in shared with `topic`/`service` labels but no service calls `.inc()` on it |

All three previously-identified metric gaps are now wired: `trades_stored_total` (consumer lag vs matching engine), `orders_processed_total{status="approved|rejected"}` (order validation rejection rate), and `violations_detected_total{rule,severity}` (compliance rule hit rate per rule). Prometheus alerting rules remain the next gap.

### Recommended Screenshots for Portfolio

1. **Grafana overview** - Dashboard with all 4 rows expanded, live data flowing after dropping a batch of sample orders
2. **Matching latency gauge** - P99 < 1 ms demonstrating in-process matching speed
3. **Trade execution spike** - `trades_executed_total` rate climbing when a crossing pair is dropped
4. **Order book depth** - buy/sell gauge showing resting orders accumulate then clear on a match
5. **Prometheus targets** - `http://localhost:9090/targets` showing all 3 scrape targets green (`UP`)
6. **Distributed trace waterfall** - Grafana Explore → Tempo, a single order's four-service span chain with `order.id` and `order.symbol` attributes visible

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
- **Gauge for state** - `fix_sessions_active` and `orders_in_book` are gauges - values that go up and down, not monotonic. `fix_sessions_active` is incremented on Logon and decremented when the TCP connection closes, so it always reflects current connected clients rather than a monotonically growing count.
- **Separate metrics port** - fix-gateway and matching-engine expose metrics on dedicated ports (8001, 8003), keeping business traffic and observability traffic on separate sockets.

---

## Engineering Highlights

**Protocol-level engineering** - Implements FIX tag=value parsing, message type routing, and per-client session state from scratch. No FIX library dependency.

**Stateful matching engine** - Price-time priority order book with partial fill support. Orders rest in the book until a crossing counterpart arrives. Book state is entirely in-memory, consistent with how real matching engines operate before persistence layers.

**Change-detected event publishing** - The market data service tracks `(best_bid, best_ask, last_trade_price)` as a tuple and suppresses publication if nothing changed - reducing downstream noise without a polling interval.

**RegTech compliance and surveillance module** - A purpose-built compliance microservice that passively observes the order pipeline. Ten rules across two categories: six compliance checks (missing client ID, invalid instrument, market hours, trade size, price deviation, duplicate detection) and four surveillance detections (wash trading, rapid-fire bursts, volume spikes, repeated order patterns). Rules are YAML-configurable at runtime with no code change required. Violations are persisted with SHA-256 tamper-evident audit trail records and a per-client risk scoring model weighted by severity - the same pattern used in regulatory reporting systems.

**Kubernetes-ready deployment** - Raw manifests (`k8s/`) and a parameterised Helm chart (`helm/fixflux/`) cover all services. StatefulSets for Redpanda and PostgreSQL with PersistentVolumeClaims, a HorizontalPodAutoscaler on the matching engine (1-5 replicas at 70% CPU), and a ConfigMap-mounted compliance policy file so rules can be changed without rebuilding the image. Every application service is stateless and twelve-factor compliant, making the transition from Docker Compose to Kubernetes require no Python changes.

**Seven independent CI pipelines** - Six per-service pipelines are path-filtered so only the changed service's pipeline runs on a PR; all six run daily. A seventh dedicated E2E pipeline starts the full Docker stack and runs the end-to-end BDD suite on a weekly schedule and on manual dispatch. Coverage is enforced at 85% across all services; lint toolchain (ruff, black, isort, mypy) is fully configured in each service's `pyproject.toml` so local and CI behaviour are identical.

**Dead letter queue** - The filedrop client publishes any FIX message that fails parsing or validation to a `dead_letter_orders` Kafka topic (`{ source_file, raw_line, error, timestamp }`) before moving the file to `rejected/`. This makes failures observable, replayable, and alertable without manual log trawling - the same pattern used for error handling in production event-driven systems.

**Three-pillar observability** - Structured log lines to stdout with `pre_trade_decision` and `compliance_decision` decision events emitted by risk-service and compliance-service on every order; Loki + Promtail collect all container logs and make them queryable from Grafana Explore with LogQL. Prometheus metrics instrumented across three services; Grafana dashboard auto-provisioned with 15 panels covering FIX message rates, matching latency (P50/P99), order book depth, cumulative trade counts, and API error rates. Distributed tracing via OpenTelemetry SDK + Tempo: every order generates a four-service trace (`order-service → risk-service → matching-engine → trade-store`) with context propagated through Kafka message payloads and queryable from Grafana Explore. All three pillars - metrics, logs, traces - are wired from a single `docker compose --profile monitoring` flag.

**Shared internal library pattern** - Cross-cutting concerns (Pydantic schemas, Kafka factory, SQLAlchemy session, exception hierarchy) are extracted into a versioned internal package, mirroring how platform teams in larger engineering organisations manage shared infrastructure.

---

## Future Improvements

| Area | Complexity | Detail |
|---|---|---|
| ~~Wire `trades_stored_total`~~ | ~~Low~~ | **Done.** `trades_stored.labels(symbol=...).inc()` is called in `trade-store/consumer.py` after each successful `repo.save()`. Graph `rate(trades_stored_total[1m])` against `rate(trades_executed_total[1m])` in Grafana to see consumer lag as a live rate divergence. |
| ~~Instrument order-service & compliance-service~~ | ~~Low~~ | **Done.** `orders_processed.labels(status="approved\|rejected").inc()` wired in order-service consumer; `violations_detected.labels(rule=..., severity=...).inc()` wired in compliance-service consumer for each rule that fires. |
| FIX TCP session | Medium | Full logout (`35=5`) handling and session expiry via heartbeat timeout; Logon + TCP disconnect lifecycle is already implemented. |
| WebSocket market data | Medium | Add an async FastAPI WebSocket endpoint to market-data-service that broadcasts change-detected snapshots to connected clients in real time. Removes the need for algorithmic trading stubs to poll a REST endpoint, and demonstrates async server-push over a persistent connection. |
| Prometheus alerting rules | Medium | Write a `prometheus_alerts.yml` defining real thresholds: P99 matching latency > 10 ms for 2 min, trade-store 5xx rate > 5/min, Kafka consumer lag > 1000 messages, compliance violation rate spike. Wire into AlertManager for notification routing. Currently all monitoring is purely observational. |
| SLIs / SLOs | Medium | Formal SLI definitions (e.g. 99.9% of `GET /trades` requests < 200 ms) with Grafana error budget burn-rate panels. Prerequisite for meaningful on-call escalation policy and production readiness review. |
| OPERATIONS.md runbooks | Medium | Create `OPERATIONS.md` with a runbook per alert: symptoms, diagnosis steps, remediation, and rollback. Linked from AlertManager annotations. Demonstrates the ability to debug your own architecture under simulated stress - a strong differentiator in SRE and production engineering interviews. |
| FIX replay | Medium | Ability to replay historical FIX message files against the live pipeline for backtesting and regression testing. |
| Schema registry | High | Confluent Schema Registry for Avro/Protobuf event versioning with schema evolution enforcement at the producer and consumer boundary. |
| Async I/O (aiokafka) | High | Replace blocking Kafka consumers in order-service and market-data-service with `aiokafka` async consumers. Allows each service to handle concurrent I/O, metrics scraping, and health endpoints in a single event loop without blocking the primary consumption thread. Required groundwork before horizontal scaling removes GIL contention as the bottleneck. |

---

## License

MIT
