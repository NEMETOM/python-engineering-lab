# FIX Protocol Simulator

A lightweight Python implementation of a FIX (Financial Information eXchange) protocol exchange simulator. It includes a TCP server, an order book, a matching engine, a FIX client, and BDD/unit test coverage.

---

## Project Structure

```
fix-protocol-simulator/
├── src/fix_simulator/
│   ├── config/          # Settings (host, port, comp IDs)
│   ├── protocol/        # FIX message, parser, constants
│   ├── exchange/        # Order, OrderBook, MatchingEngine, ExecutionReports
│   ├── server/          # Async TCP FIX server
│   ├── client/          # FIX client (send orders, receive reports)
│   ├── simulation/      # Entry point for running the simulation
│   └── utils/           # Logger setup
├── scripts/
│   ├── run_exchange_simulator.py   # Start the exchange server
│   └── run_client.py               # Connect and send a sample order
├── tests/
│   ├── test_*.py        # Unit tests (pytest)
│   └── bdd/
│       ├── features/    # Gherkin scenarios
│       └── steps/       # Step definitions (behave)
└── pyproject.toml
```

---

## Installation

```bash
pip install -e .[dev]
```

---

## Running the Simulator

Start the exchange server in one terminal:

```bash
python scripts/run_exchange_simulator.py
```

Send a sample `NewOrderSingle` from a second terminal:

```bash
python scripts/run_client.py
```

Expected server output:

```
2026-03-15 10:02:11 | INFO | fix_server | FIX server running 127.0.0.1:9878
2026-03-15 10:02:20 | INFO | fix_server | Client connected ('127.0.0.1', 50122)
2026-03-15 10:02:21 | INFO | fix_server | Received 35=D|49=CLIENT|...
2026-03-15 10:02:21 | INFO | fix_parser | Parsing FIX message
```

---

## Configuration

Defaults are defined in `src/fix_simulator/config/settings.py`:

| Setting              | Default     |
|----------------------|-------------|
| `host`               | `127.0.0.1` |
| `port`               | `9878`      |
| `sender_comp_id`     | `EXCHANGE`  |
| `target_comp_id`     | `CLIENT`    |
| `heartbeat_interval` | `30`        |

---

## FIX Message Support

| Message Type   | Tag `35=` |
|----------------|-----------|
| Logon          | `A`       |
| Heartbeat      | `0`       |
| NewOrderSingle | `D`       |
| ExecutionReport| `8`       |
| OrderCancel    | `F`       |

---

## Order Matching

The `MatchingEngine` implements price-priority matching:

- A **BUY** order matches the best (lowest) ask if `buy_price >= ask_price`
- A **SELL** order matches the best (highest) bid if `sell_price <= bid_price`
- Trades execute at the **resting order's price**
- Unmatched orders are added to the order book

---

## Testing

### Unit Tests

```bash
pytest --cov=fix_simulator --cov-report=term-missing
```

Coverage threshold: **75%** (currently ~84%)

### BDD Tests

```bash
python -m behave tests/bdd/features/
```

BDD scenarios cover:

- Matching buy and sell orders
- No match when prices don't cross
- Partial fill using minimum quantity
- SELL matching the best BID from multiple buy orders
- Parameterised trade outcome scenarios

---

## CI/CD

GitHub Actions runs on push to `main`/`develop` and weekly on Mondays:

- Ruff lint
- Black formatting check
- isort import check
- MyPy type checking
- Pytest with coverage enforcement
- Behave BDD tests
