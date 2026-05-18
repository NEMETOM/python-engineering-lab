# How to Run: order-service

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
- **fix-gateway** — produces raw FIX orders onto the `raw_orders` topic
- **market-data-service** — market data feed
- **order-service** *(add to `docker-compose.yml` if not yet present — see below)*

### 2. Add order-service to docker-compose.yml

If `order-service` is not yet declared in the Compose file, append the following service block:

```yaml
  order-service:
    build: ./services/order-service
    depends_on:
      - kafka
    environment:
      KAFKA_BROKER: kafka:9092
```

Then re-run:

```bash
docker compose up --build order-service
```

### 3. Run only the order-service (stack already up)

```bash
docker compose up order-service
```

### 4. View logs

```bash
docker compose logs -f order-service
```

### 5. Tear down

```bash
docker compose down
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `KAFKA_BROKER` | `kafka:9092` | Kafka bootstrap server address |

---

## Running Tests

From `services/order-service/`:

```bash
# Unit tests
pytest tests/unit

# BDD tests
behave tests/bdd/features
```

---

## Definition of Done

- [x] Consumes `raw_orders`
- [x] Validates correctly
- [x] Rejects invalid orders
- [x] Produces `validated_orders`
- [x] Logs clearly
- [x] Tests pass
- [x] Runs in Docker
- [x] Integrates with matching-engine
