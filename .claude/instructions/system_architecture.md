# FixFlux — System Architecture

This describes the architecture **as it actually exists in this repo**, verified against the
source, not an idealized target. FixFlux is not Hexagonal/Ports-and-Adapters and is not DDD in
the formal sense (no domain-service layer, no repository interfaces abstracted behind ports). It's
a set of small, single-purpose services connected by Kafka topics, each following the same plain
layered structure. That simplicity is deliberate — do not introduce ports/adapters/domain-service
abstractions into a service unless there's a concrete reason tied to a real requirement.

## The shape of one service

Every service under `fixflux/services/<name>/src/<name>/` follows the same layout:

```
<name>/
├── consumer.py        # for msg in consumer: ... — the Kafka intake loop (synchronous)
├── producer.py        # thin wrapper sending outbound events to specific topics
├── models.py           # plain @dataclass objects for in-process, mutable state (see below)
├── schemas/            # Pydantic BaseModel classes for anything crossing a Kafka/HTTP boundary
├── config.py           # a Settings/constants module reading os.getenv(...)
├── infrastructure/
│   └── kafka_client.py # re-exports create_producer/create_consumer from shared/
├── utils/logger.py     # re-exports configure_logging/get_logger from shared/
└── api/                # only present if the service has an HTTP surface (see below)
```

`dataclass` vs Pydantic `BaseModel` is a deliberate distinction, not inconsistency:
- **dataclass** (`matching_engine.models.Order`, `.Trade`) — in-process objects mutated during a
  hot loop (e.g. `order.quantity -= trade_qty` inside the matching loop). No validation needed;
  the data never crossed a serialization boundary before this point.
- **Pydantic `BaseModel`** — anything that arrived over Kafka or HTTP, or is about to be sent over
  either. Validation at the boundary is the point.

## Services and the topics between them

```
FIX file (filedrop)
  └─► fix-gateway            parses tag=value FIX text
        └─► raw_orders
              ├─► order-service    validates/enriches  └─► validated_orders
              ├─► risk-service     MiFID II pre-trade checks (notional/fat-finger/position/open-orders)
              │     ├─► risk_approved_orders
              │     ├─► risk_rejected_orders
              │     └─► execution_reports (New/Rejected)
              └─► compliance-consumer   passive surveillance, never blocks  └─► Postgres (audit + violations)
        risk_approved_orders
              └─► matching-engine   price-time priority, two plain Python lists (order_book.py)
                    ├─► trades
                    ├─► order_book_updates   (tagged by symbol — see market-data-service note below)
                    └─► execution_reports (Fill)
        trades + order_book_updates
              └─► market-data-service   per-symbol (best_bid, best_ask, last_trade_price) cache,
                    publishes only on change  └─► market_data
        market_data
              └─► market-data-api   consumes on a background thread, broadcasts to WebSocket
                    clients at /ws/market-data (see coding_standards.md for the async exception this is)
        trades
              └─► trade-store-consumer  └─► Postgres (trades table)
```

**`raw_orders`, `risk_approved_orders`, and `trades` are single-partition, single-replica** —
confirmed directly via `rpk topic describe`. The other topics are created the same way (no
explicit partition count passed anywhere in `cleanup.sh`'s topic (re)creation, which covers all of
them), so almost certainly the same, but only those three were checked directly — verify before
asserting it about a specific one you haven't checked yourself. Either way this is a real, current
scaling ceiling, not an oversight to silently "fix" — see `fixflux/PERFORMANCE_BOTTLENECKS.md`
(gitignored, ask the user if you need its contents) before proposing partitioning changes.

## HTTP surfaces (not every service has one)

- **compliance-service** (`compliance-api` container) — the "FixFlux Console": a unified FastAPI
  app with two tabs sharing one Jinja2 shell template (`templates/_shell.html`) — the FIX message
  injector at `/` (`fix_parser.py` + `injector_producer.py` + `POST /api/orders/inject`) and the
  compliance rules admin panel at `/admin/compliance` (toggle rules live via
  `compliance_rule_overrides` in Postgres, picked up by `compliance-consumer` on a 5s poll). A
  separate `compliance-consumer` container (same image, different `command:`) runs the actual
  rule-evaluation threads that *consume* `raw_orders`/`validated_orders` for surveillance —
  `compliance-api` only *produces* to `raw_orders` (via the injector), it never consumes either
  topic itself.
- **trade-store** — plain REST (`GET /trades`), backed by Postgres. A separate
  `trade-store-consumer` container does the actual Kafka→Postgres persistence.
- **matching-engine** and **risk-service** — no HTTP surface at all beyond a Prometheus
  `/metrics` endpoint (`prometheus_client.start_http_server`). Don't add REST routes to these
  without a concrete reason; there's a specific reason FIX injection and the admin panel live in
  compliance-service instead (see `system_architecture.md`'s HTTP surfaces list above for why:
  every service that needs both a consumer loop and an HTTP API in this repo splits them into two
  sibling containers from the same image, not one process doing both).
- **market-data-api** — the one WebSocket surface, described in `coding_standards.md`.

## The `shared/` library

Every service depends on `shared/` (installed via `pip install -e ./shared`, or `COPY shared
./shared` in each Dockerfile). It provides:

- `shared/infrastructure/kafka_client.py` — **the single Kafka producer/consumer factory every
  service uses.** `enable_idempotence=False` is deliberate (see the docstring/commit history —
  idle idempotent producers had their broker-side producer ID expire and silently dropped the
  first message after a long gap; these topics are at-least-once already, so idempotence bought
  nothing and cost data loss). Never construct a raw `KafkaProducer`/`KafkaConsumer` outside this
  factory.
- `shared/observability/` — `log_config.py` (structured logging, see `coding_standards.md`),
  `metrics.py` (the one Prometheus registry every service's counters/histograms live in),
  `tracing.py` (manual trace-context propagation — `inject_ctx`/`extract_ctx` write/read
  `_trace_id`/`_span_id` directly into the Kafka message dict, because messages are plain JSON
  dicts with no native trace-carrier support, not because of any general aversion to
  auto-instrumentation).
- `shared/config/_loader.py` — `build_db_url()`: `DATABASE_URL` env var if set, else reads
  `config.yaml`.

## Infrastructure

Redpanda (Kafka API-compatible), PostgreSQL, Prometheus + Grafana + Loki + Tempo, all defined in
one `fixflux/docker-compose.yml` with named `profiles` (`pipeline`, `full`, `monitoring`). Deployed
to a single DigitalOcean droplet; `deploy.yml` does `git pull` + `docker compose build` + `up -d`
over SSH on every push to `main` touching `fixflux/**`. There is no Kubernetes, no service mesh, no
multi-region anything — keep proposals proportionate to a single 2 vCPU / 4GB droplet.
