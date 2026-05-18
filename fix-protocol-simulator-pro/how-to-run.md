# How to Run fix-protocol-simulator-pro

## Prerequisites

- Docker Desktop running
- Python 3.11+ installed locally

---

## Step 1 - Clone and navigate

```bash
git clone https://github.com/NEMETOM/python-engineering-lab.git
cd python-engineering-lab/fix-protocol-simulator-pro
```

---

## Step 2 - Create the local DB config (for local scripts only)

```bash
cp shared/config/config.yaml.example shared/config/config.yaml
```

No edits needed - the defaults match the Docker postgres credentials.

---

## Step 3 - Start all services

```bash
docker-compose up --build
```

Wait until trade-store starts up (it is last - it waits for kafka and postgres health checks).
Takes ~60-90 seconds on first build.

---

## Step 4 - Verify everything is up

```bash
docker-compose ps
```

All 8 containers should show `running`: zookeeper, kafka, postgres, fix-gateway, order-service,
matching-engine, market-data-service, trade-store.

Check the API is live: `http://localhost:8000/docs`

---

## Step 5 - Start the file-drop watcher (separate terminal)

The watcher imports `shared/` and `fix-gateway`, so both must be on the Python path.
Run from the `fix-protocol-simulator-pro/` directory:

```bash
pip install kafka-python pydantic  # one-time
PYTHONPATH=.:services/fix-gateway/src python clients/fix-filedrop-client/watcher.py
```

On Windows (PowerShell):

```powershell
$env:PYTHONPATH = ".;services/fix-gateway/src"
python clients/fix-filedrop-client/watcher.py
```

---

## Step 6 - Drop a FIX order file

Copy any valid file from `data/` into the filedrop directory:

```bash
cp data/order_buy_btcusd_001.txt clients/fix-filedrop-client/filedrop/
```

The watcher picks it up within a few seconds, parses it, publishes to Kafka, and moves it
to `processed/`.

---

## Step 7 - Verify the trade was stored

```bash
curl http://localhost:8000/trades
```

Or open `http://localhost:8000/docs` and use `GET /trades` in Swagger.

---

## Optional - run the DB connectivity test

With the stack running:

```bash
python scripts/test_db_connection.py
```

Inserts a test record, reads it back, and prints the full trades table.

---

## Teardown

```bash
docker-compose down      # stops containers, keeps postgres volume
docker-compose down -v   # stops containers AND wipes the database
```

---

## Notes

### Matching requires overlapping prices

The matching engine only produces a trade when a buy price >= a sell price for the same symbol.
Example pairs from `data/` that will match:

| Buy file | Buy price | Sell file | Sell price |
|---|---|---|---|
| `order_buy_btcusd_001.txt` | 50000.00 | `order_sell_btcusd_001.txt` | 50500.00 | no match |
| `order_buy_btcusd_002.txt` | 49500.00 | `order_sell_btcusd_003.txt` | 50250.00 | no match |
| `order_buy_ethusd_001.txt` | 3000.00 | `order_sell_ethusd_001.txt` | 3100.00 | no match |

To force a match, drop a buy and a sell for the same symbol where buy price >= sell price.
The simplest approach is to drop the same symbol twice - once as BUY, once as SELL at a lower price.

### Sample files overview

Valid files (go to `processed/`):

| File | Side | Symbol | Price | Qty |
|---|---|---|---|---|
| `order_buy_btcusd_001.txt` | BUY | BTCUSD | 50000.00 | 1 |
| `order_buy_btcusd_002.txt` | BUY | BTCUSD | 49500.00 | 5 |
| `order_buy_btcusd_003.txt` | BUY | BTCUSD | 48750.00 | 2 |
| `order_sell_btcusd_001.txt` | SELL | BTCUSD | 50500.00 | 2 |
| `order_sell_btcusd_002.txt` | SELL | BTCUSD | 51000.00 | 3 |
| `order_sell_btcusd_003.txt` | SELL | BTCUSD | 50250.00 | 1 |
| `order_buy_ethusd_001.txt` | BUY | ETHUSD | 3000.00 | 10 |
| `order_buy_ethusd_002.txt` | BUY | ETHUSD | 2950.00 | 20 |
| `order_sell_ethusd_001.txt` | SELL | ETHUSD | 3100.00 | 5 |
| `order_sell_ethusd_002.txt` | SELL | ETHUSD | 3050.00 | 15 |
| `order_buy_aapl_001.txt` | BUY | AAPL | 175.50 | 100 |
| `order_sell_aapl_001.txt` | SELL | AAPL | 178.00 | 50 |

Invalid files (go to `rejected/`):

| File | Reason |
|---|---|
| `order_invalid_missing_side.txt` | missing tag 54 (Side) |
| `order_invalid_wrong_msgtype.txt` | `35=E` - only NewOrderSingle (`35=D`) supported |
