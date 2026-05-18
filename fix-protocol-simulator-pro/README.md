# FIX Protocol Simulator Pro

An event-driven trading system simulator built with Python, Kafka, and Docker.

This project simulates a simplified exchange architecture including FIX ingestion, order validation, matching engine, market data streaming, and trade storage with API access.

---

## Architecture Overview

```
FIX Client / File Drop
        │
        ▼
  FIX Gateway
        ▼
  Redpanda (raw_orders)
        ▼
  Order Service
        ▼
  Matching Engine
   │           │
   ▼           ▼
Market Data   Trade Store
   │              │
   ▼              ▼
Kafka Topic     PostgreSQL
                  │
                  ▼
               FastAPI
```

---

## Services

| Service | Kafka topics | Responsibility |
|---|---|---|
| **fix-gateway** | produces → `raw_orders` | Accepts FIX messages from external clients (file drop or TCP). Parses `tag=value` fields, identifies message type (Logon, Heartbeat, NewOrderSingle), and publishes raw order events. Manages per-client session state. |
| **order-service** | consumes `raw_orders`, produces → `validated_orders` | Validates business rules: price and quantity must be positive, side must be `BUY` or `SELL`. Enriches passing orders with a UUID order ID. Drops and logs invalid orders without crashing. |
| **matching-engine** | consumes `validated_orders`, produces → `trades`, `order_book` | Maintains an in-memory order book with price-time priority. Matches buy/sell orders when prices cross and emits trade events. Publishes an order book snapshot after each successful match. |
| **market-data-service** | consumes `trades`, `order_book` | Caches the latest best bid, best ask, and last trade price from incoming events. Publishes a market data summary on a configurable interval (default: 10 s). |
| **trade-store** | consumes `trades` | Persists each trade event to PostgreSQL. Exposes a FastAPI REST API (`GET /trades`, `GET /trades/{id}`, `GET /health`) for querying stored trades. |
| **shared** | - | Internal library used by all services. Provides Kafka client helpers, Pydantic schemas, structured logging, SQLAlchemy DB setup, and custom exception types. |
| **fix-filedrop-client** | - | Local watcher script (not a Docker service). Monitors a directory for FIX message files, forwards each to the FIX gateway via Kafka, then moves the file to `processed/` or `rejected/`. |

---

## Tech Stack

* Python 3.11+
* Redpanda v23.3.21 (Kafka-compatible, no JVM, no Zookeeper)
* PostgreSQL 15
* FastAPI + uvicorn
* Docker & Docker Compose

---

## Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop/) 24+
* Docker Compose v2 (bundled with Docker Desktop)
* Python 3.11+ (only needed to run the local file-drop watcher)

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/NEMETOM/python-engineering-lab.git
cd python-engineering-lab/fix-protocol-simulator-pro
```

---

### 2. Create the database config file (local scripts only)

This step is only required if you want to run local scripts such as `scripts/test_db_connection.py`.
Docker services use the `DATABASE_URL` environment variable defined in `docker-compose.yml` instead.

```bash
cp shared/config/config.yaml.example shared/config/config.yaml
```

The default credentials in `config.yaml.example` match what `docker-compose.yml` configures for
the `postgres` container, so no edits are needed unless you change the database credentials.

---

### 3. Build and start all services

Run from the `fix-protocol-simulator-pro/` directory.

Services are grouped into **profiles** so you can start only what you need:

| Profile | Services started |
|---|---|
| _(none)_ | `redpanda`, `postgres` only |
| `pipeline` | + `fix-gateway`, `order-service`, `matching-engine`, `trade-store` |
| `full` | + all of the above + `market-data-service` |

**Start everything (full stack):**

```bash
docker compose --profile full up --build
```

**Start the pipeline without market-data-service:**

```bash
docker compose --profile pipeline up --build
```

**Start individual services by name:**

Name any services explicitly - Docker Compose resolves `depends_on` automatically, so infrastructure services (`redpanda`, `postgres`) start alongside:

```bash
# Matching engine only (redpanda starts automatically via depends_on)
docker compose up redpanda matching-engine

# Matching engine + trade store
docker compose up redpanda postgres matching-engine trade-store

# Just infrastructure (broker + DB)
docker compose up redpanda postgres
```

> Profiled services (`fix-gateway`, `order-service`, etc.) are excluded from a plain `docker compose up` with no `--profile` option. Naming them explicitly on the command line bypasses that restriction.

Redpanda and Postgres have health checks - dependent services wait until both are ready before starting.

> **Note:** None of the above starts the file-drop watcher.
> To drop FIX messages into the filedrop folder, run `watcher.py` separately
> in a local terminal after the stack is up (see step 6).

---

### 4. Verify all containers are up

```bash
docker compose ps
```

All services should show `running` or `Up`. Expected output (after `--profile full`):

| Name | State | Ports |
|---|---|---|
| fix-protocol-simulator-pro-redpanda-1 | Up (healthy) | 0.0.0.0:9092→29092/tcp |
| fix-protocol-simulator-pro-postgres-1 | Up (healthy) | 0.0.0.0:5433→5432/tcp |
| fix-protocol-simulator-pro-fix-gateway-1 | Up | - |
| fix-protocol-simulator-pro-order-service-1 | Up | - |
| fix-protocol-simulator-pro-matching-engine-1 | Up | - |
| fix-protocol-simulator-pro-market-data-service-1 | Up | - |
| fix-protocol-simulator-pro-trade-store-1 | Up | 0.0.0.0:8000→8000/tcp |

Key things to check:
- `redpanda` and `postgres` must show `(healthy)` — application services wait for these before starting
- `trade-store` exposes port `8000` (REST API)
- `redpanda` exposes port `9092` on the host for the local file-drop watcher
- `postgres` exposes port `5433` on the host (your local PostgreSQL keeps `5432`)
- `fix-gateway`, `order-service`, `matching-engine`, and `market-data-service` have no host-exposed ports — they communicate only via Redpanda inside the Docker network

---

### 5. Access the Trade Store API

Swagger UI:

```
http://localhost:8000/docs
```

Available endpoints:

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/trades` | List all trades (optional `?symbol=BTCUSD`) |
| GET | `/trades/{trade_id}` | Get a single trade by ID |

> **Note:** only matched trades appear here. An order that does not find a counterpart rests in the matching engine's in-memory order book and never reaches the database or this API.

---

### 6. Run the FIX file-drop watcher (separate terminal)

The watcher monitors a local directory for FIX message files and forwards them to the FIX gateway
via Kafka. Run it locally (not in Docker) from the `fix-protocol-simulator-pro/` directory.

**One-time setup** (installs `shared` and `fix-gateway` as local packages):

```bash
pip install -e shared
pip install -e services/fix-gateway
```

**Run the watcher:**

```bash
# Linux / macOS
python clients/fix-filedrop-client/watcher.py

# Windows PowerShell
python clients\fix-filedrop-client\watcher.py
```

> The `pip install -e` steps make `shared` and `fix_gateway` importable without setting `PYTHONPATH` manually. The `-e` (editable) flag means changes to those packages are reflected immediately without reinstalling.

---

### 7. Drop a FIX order file

Create a file at:

```
clients/fix-filedrop-client/filedrop/order_001.txt
```

Example content:

```
35=D|55=BTCUSD|54=1|44=50000|38=1|
```

Fields are pipe-delimited (`|`). Each `tag=value` pair must be followed by a `|`.

What happens next:
1. Watcher detects the file
2. FIX message is parsed and validated
3. Event published to Kafka topic `raw_orders`
4. Order Service validates and forwards to `validated_orders`
5. Matching Engine matches orders and publishes to `trades` - **only if a counterpart order exists at a crossing price**
6. Trade Store persists to PostgreSQL
7. File moves to `processed/` (or `rejected/` if invalid)

> Unmatched orders rest in the matching engine's in-memory order book until a crossing counterpart arrives. They are never written to the database.

---

## Testing Database Connectivity

With the stack running (`docker compose up`), test the local DB connection using:

```bash
python scripts/test_db_connection.py
```

This connects via `shared/config/config.yaml` (host `localhost`, port `5433` - the exposed port),
inserts a test record, reads it back, prints the full trades table, then exits.

---

## Invalid FIX File Example

Missing required tag (side tag `54` absent):

```
35=D|55=BTCUSD|44=50000|38=1|
```

Result: file moves to `rejected/`, error logged by watcher.

---

## Environment Variables

These are set automatically inside containers by `docker-compose.yml`. Listed here for reference
or if running services outside Docker:

| Variable | Default | Used by |
|---|---|---|
| `KAFKA_BROKER` | `localhost:9092` | all services |
| `DATABASE_URL` | _(reads config.yaml)_ | trade-store |
| `LOG_LEVEL` | `INFO` | all services |
| `LOG_FORMAT` | `plain` | all services (`json` for structured logs) |

---

## Project Structure

```
fix-protocol-simulator-pro/
  docker-compose.yml
  services/            - microservices (each has its own Dockerfile + pyproject.toml)
    fix-gateway/
    order-service/
    matching-engine/
    market-data-service/
    trade-store/
  shared/              - internal platform library (schemas, logging, kafka, db)
  clients/             - external simulators
    fix-filedrop-client/
  scripts/             - local utility scripts
```

---

## Running Tests

### Component unit tests

Run pytest from inside the service or `shared/` directory:

```bash
cd services/trade-store
python -m pytest -v

cd services/order-service
python -m pytest -v

cd services/matching-engine
python -m pytest -v

cd services/market-data-service
python -m pytest -v

cd shared
python -m pytest -v
```

### Component BDD tests

Run behave from inside the service or `shared/` directory:

```bash
cd services/trade-store
python -m behave tests/bdd/features/

cd services/order-service
python -m behave tests/bdd/features/

cd services/matching-engine
python -m behave tests/bdd/features/

cd services/market-data-service
python -m behave tests/bdd/features/

cd shared
python -m behave tests/bdd/features/
```

### Integration tests

Integration tests require real infrastructure. Start the minimum required services first:

**Trade persistence tests** (PostgreSQL only):

```bash
docker compose up -d postgres
```

**Kafka pipeline tests** (PostgreSQL + Redpanda):

```bash
docker compose up -d postgres redpanda
```

Then run from the `tests/integration/` directory:

```bash
cd tests/integration
python -m behave features/
```

To run only the persistence tests (no Kafka required):

```bash
cd tests/integration
python -m behave features/ --tags="@integration" --tags="~@needs_kafka"
```

To run only the Kafka pipeline tests:

```bash
cd tests/integration
python -m behave features/ --tags="@needs_kafka"
```

The tests connect via `DATABASE_URL` / `KAFKA_BROKER` environment variables,
falling back to `localhost` defaults - the same values used by `config.yaml.example`.

**Dependencies** (if not already installed):

```bash
pip install sqlalchemy psycopg2-binary fastapi httpx kafka-python pydantic pyyaml
```

---

## Features

* FIX message ingestion (file-based)
* Event-driven architecture (Redpanda / Kafka-compatible)
* Matching engine with order book
* Market data generation
* Trade persistence (PostgreSQL)
* REST API (FastAPI + Swagger)
* Shared internal platform module

---

## Design Standards

This project is structured around several well-established industry standards.

### Python Packaging (PyPA src layout + PEP 517/518)

Each service uses the `src/` layout recommended by the [Python Packaging User Guide](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/), with a `pyproject.toml` declaring the build system (PEP 517/518). This prevents accidental imports of uninstalled packages and keeps source separate from tests and config.

```
services/order-service/
  src/order_service/   ← installable package
  tests/               ← not part of the package
  pyproject.toml       ← PEP 517/518 build declaration
```

### The Twelve-Factor App

The project follows the [12-Factor methodology](https://12factor.net/) for cloud-native services:

| Factor | How it applies |
|---|---|
| Config | All runtime config via environment variables (`KAFKA_BROKER`, `DATABASE_URL`, `LOG_LEVEL`) |
| Backing services | Kafka and PostgreSQL treated as attached resources, not embedded dependencies |
| Build / release / run | Each service has its own Dockerfile; `docker-compose.yml` handles orchestration |
| Processes | Stateless consumers; Kafka holds all durable state between services |
| Logs | Structured JSON logging; services write to stdout, not files |
| Admin processes | One-off scripts live in `scripts/`, separate from application code |

### Microservices with Bounded Contexts (DDD)

Each service owns a single bounded context from Domain-Driven Design - FIX ingestion, order validation, matching, market data, trade persistence. They communicate exclusively through Kafka events (no direct service-to-service calls), which matches the pattern described in Sam Newman's *Building Microservices* and Martin Fowler's writings on event-driven architecture.

### Hexagonal Architecture (Ports and Adapters)

Inside each service, infrastructure concerns (Kafka client, DB session) are isolated in `infrastructure/`, keeping domain logic (validator, engine, transformer) free of framework dependencies. This is Alistair Cockburn's hexagonal architecture pattern.

### BDD with Gherkin

Tests are structured as three layers - component BDD, shared-module BDD, and integration BDD - using [behave](https://behave.readthedocs.io/) with Gherkin feature files. Feature files and step implementations are kept as siblings (`features/` and `steps/` under `tests/bdd/`), which separates the specification from its implementation.

### Who uses these patterns

These patterns appear in production systems at:

- **Bloomberg / Fidessa / ION Trading** - FIX protocol pipelines with event-driven order routing
- **Coinbase, Kraken, Robinhood** - Kafka-based trade pipelines with microservice boundaries similar to the matching engine / trade-store split here
- **Uber, Airbnb** - Python src layout with internal shared libraries installed across services
- **Netflix, Confluent** - Kafka-centric event-driven architectures with per-service Docker images and health-check-gated startup ordering
- **Thoughtworks** (Martin Fowler) - Advocates for this exact microservices + bounded context + event-driven combination as the canonical pattern for financial and marketplace platforms

---

## Future Improvements

* FIX TCP session support (logon, heartbeat)
* WebSocket market data streaming
* Kubernetes deployment
* Observability (metrics, tracing)
* Schema versioning

---

## Author Notes

This project demonstrates:

* microservices design
* event-driven systems
* clean architecture with shared modules
* production-style logging and validation

---

## License

MIT
