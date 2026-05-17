# How to Run: trade-store

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Repository cloned locally

---

## Running with Docker Compose

All commands are run from the repository root (`fix-protocol-simulator-pro/`).

### 1. Start the full stack

```bash
docker compose up --build
```

This starts:
- **zookeeper** — Kafka coordination
- **kafka** — message broker on `kafka:9092`
- **postgres** — PostgreSQL 15 on port `5432`, database `trades`
- **trade-store** — consumes the `trades` topic and persists to PostgreSQL
- **matching-engine** *(if present)* — produces trade events onto the `trades` topic

### 2. Start only trade-store and its dependencies

```bash
docker compose up --build trade-store
```

Compose will automatically start `kafka` and `postgres` first due to `depends_on`.

### 3. View logs

```bash
docker compose logs -f trade-store
```

### 4. Tear down

```bash
docker compose down
```

To also remove the PostgreSQL volume (wipes stored trades):

```bash
docker compose down -v
```

---

## Database

trade-store uses SQLAlchemy with the following table:

| Column | Type | Notes |
|---|---|---|
| `trade_id` | String | Primary key |
| `symbol` | String | |
| `buy_order_id` | String | |
| `sell_order_id` | String | |
| `price` | Float | |
| `quantity` | Integer | |
| `timestamp` | DateTime | |

The table is created automatically on startup via `Base.metadata.create_all()`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `KAFKA_BROKER` | `kafka:9092` | Kafka bootstrap server address |
| `DATABASE_URL` | `postgresql://user:password@postgres:5432/trades` | SQLAlchemy connection string |

---

## Running Tests

From `services/trade-store/`:

```bash
# Unit tests
pytest tests/unit
```

---

## Definition of Done

- [x] Consumes `trades`
- [x] Stores in PostgreSQL
- [x] No crashes on bad data
- [x] Logs clearly
- [x] DB table exists
- [x] Docker works
- [x] Integrated with matching-engine
