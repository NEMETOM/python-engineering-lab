# Market Data Service – Quick Start Cheat Sheet

This guide helps you run the system and manually send events into Kafka to test the pipeline.

---

## 🧱 Step 1 — Start the system

From the project root:

```bash
docker-compose up --build
```

You should see logs from:

* Kafka
* Zookeeper
* market-data-service

---

## 🔍 Step 2 — Verify service is running

You should see logs like:

```text
publishing market data {
  'best_bid': None,
  'best_ask': None,
  'mid_price': None,
  'last_trade_price': None
}
```

This means:

✔ service is running
✔ waiting for events

---

## 📦 Step 3 — Open Kafka producer

### 1. Find Kafka container

```bash
docker ps
```

Look for something like:

```text
kafka-1
```

---

### 2. Enter container

```bash
docker exec -it kafka-1 bash
```

---

### 3. Start producer (trade events)

```bash
kafka-console-producer \
  --broker-list kafka:9092 \
  --topic trades
```

---

## 🚀 Step 4 — Send JSON event

Once the producer is running, you will see a prompt like:

```text
>
```

Now simply **paste JSON and press ENTER**:

```json
{"symbol":"BTCUSD","price":50000,"quantity":1}
```

---

## ✅ Expected result

In your service logs you should now see:

```text
received trade {'symbol': 'BTCUSD', 'price': 50000}

publishing market data {
  'last_trade_price': 50000
}
```

---

## 📊 Optional — Send order book update

Start another producer:

```bash
kafka-console-producer \
  --broker-list kafka:9092 \
  --topic order_book_updates
```

Send:

```json
{"symbol":"BTCUSD","best_bid":49990,"best_ask":50010}
```

---

## 🎯 Expected output

```text
mid_price: 50000
```

---

## ⚠️ Common issues

### Nothing happens after sending JSON

* Make sure JSON is **one line**
* Press ENTER after pasting
* Check topic name matches exactly

---

### Kafka container not found

Run:

```bash
docker ps
```

Check container name (it might not be `kafka-1`)

---

### Windows copy/paste issues

Use:

* Right-click paste OR
* `Ctrl + Shift + V`

---

## 🧠 Tip

Each line you send = **one Kafka message**

You can send multiple messages:

```json
{"symbol":"BTCUSD","price":51000,"quantity":1}
{"symbol":"BTCUSD","price":52000,"quantity":1}
```

---

## 🎉 Success condition

You’re done when:

✔ sending JSON updates logs
✔ last_trade_price changes
✔ mid_price updates after book events

---

## 🚀 Next step

Connect:

```
matching-engine → trades → market-data-service
```
