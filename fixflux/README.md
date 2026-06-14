# FIXFlux | Stateful Low-Latency FIX Protocol Engine

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

---

An event-driven exchange simulator that models a real-world order flow pipeline using the FIX protocol - from client message ingestion through order validation, price-time priority matching, market data publication, and trade persistence - with a full RegTech compliance and surveillance module running as a parallel observer. Built with Python microservices, Redpanda (Kafka-compatible), PostgreSQL, and Docker, following 12-Factor, Hexagonal Architecture, and Domain-Driven Design principles.

> Designed to reflect the architecture of production trading systems at firms such as Bloomberg, Fidessa, Coinbase, and Kraken - where FIX protocol ingestion, Kafka-based event routing, and microservice-bounded contexts are standard engineering practice.

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
│       └── tests/                   # unit + BDD tests (83 tests, 88% coverage)
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
│   └── fixflux/           # Helm chart - parameterised for dev/staging/prod
│       ├── Chart.yaml
│       ├── values.yaml              # All tuneable knobs (replicas, resources, image registry)
│       └── templates/               # Go-templated versions of all k8s/ manifests
├── tests/
│   └── integration/                 # BDD integration tests (PostgreSQL + Kafka)
└── scripts/                         # Local utility scripts (DB connectivity check, etc.)
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
| compliance-api | Up | 8010 |
| compliance-consumer | Up | - |
| prometheus | Up (monitoring profile) | 9090 |
| grafana | Up (monitoring profile) | 3000 |

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

The E2E suite (`@e2e`) exercises the complete pipeline in a single test: a FIX file is dropped into the filedrop client, flows through Kafka → order-service → matching-engine → trade-store, and the resulting trade is asserted via `GET /trades`. The full Docker stack must be running.

```bash
# Start the full pipeline
docker compose --profile full up -d

# Install test dependencies (once)
pip install -e shared && pip install -e services/fix-gateway && pip install -e services/trade-store
pip install behave kafka-python sqlalchemy psycopg2-binary

# Run E2E tests
cd tests/integration
python -m behave features/filedrop_e2e_pipeline.feature --tags="@e2e" -v
```

Two scenarios are covered:

| Scenario | What it verifies |
|---|---|
| Crossing FIX pair | Buy + sell at the same price produces a matched trade visible in the REST API within 30 s |
| Invalid message resilience | A bad FIX line is dead-lettered and does not block a subsequent valid crossing pair |

In CI, E2E tests run in a dedicated workflow (`e2e.yml`) triggered manually or on a weekly schedule - not on every push, because they require Docker infrastructure and take longer than unit tests.

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

**Production-style observability** - Structured JSON logging throughout (INFO for business events, DEBUG for infrastructure noise). Prometheus metrics instrumented across three services; Grafana dashboard auto-provisioned with 14 panels covering FIX message rates, matching latency (P50/P99), order book depth, and API error rates. Monitoring profile starts Prometheus + Grafana alongside the application stack via a single compose command.

**Shared internal library pattern** - Cross-cutting concerns (Pydantic schemas, Kafka factory, SQLAlchemy session, exception hierarchy) are extracted into a versioned internal package, mirroring how platform teams in larger engineering organisations manage shared infrastructure.

---

## Future Improvements

| Area | Detail |
|---|---|
| FIX TCP session | Full logout (`35=5`) handling and session expiry via heartbeat timeout; Logon + TCP disconnect lifecycle is already implemented |
| Multi-symbol order book | Per-symbol book isolation - currently all symbols share one book |
| WebSocket market data | Push-based streaming of market data snapshots to connected clients |
| OpenTelemetry traces | Distributed tracing across services; correlate a single order through all 4 hops |
| Schema registry | Confluent Schema Registry for Avro/Protobuf event versioning |
| Async I/O | Replace blocking Kafka consumers with asyncio-based consumers (aiokafka) |
| FIX replay | Ability to replay historical FIX message files for backtesting and regression |

---

## License

MIT
