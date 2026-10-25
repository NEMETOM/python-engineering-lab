# Demo: MiFID II post-trade reporting

Inject three order pairs through the **FIX Msg Injector**, then query `regulatory_reports` to show
how `reporting-service` classified each trade, what goes to the regulator and what would be public.
It takes about five minutes.

## What the demo shows

[`data/mifid_reporting_demo.txt`](../data/mifid_reporting_demo.txt) holds six orders that match
into three trades:

| Trade | Parties | Expected status | Why |
|---|---|---|---|
| AAPL 100 @ 175.00 | DEMO_BUYER1 / DEMO_SELLER1 | `REPORTABLE` | In scope, both LEIs known |
| EURUSD 1000 @ 1.09 | DEMO_BUYER2 / DEMO_SELLER2 | `NOT_REPORTABLE` | FX spot is out of scope in this simulator |
| MSFT 10 @ 415.00 | VOL_B0001 / TRADER2 | `INCOMPLETE` | No LEI on file for VOL_B0001 |

For the reportable AAPL trade you then show two views of the same row:
- **Restricted (regulator only):** buyer/seller LEIs, trading capacity (`DEAL`), CFI code
  (`ESVUFR`). These are RTS 22 transaction-reporting fields.
- **Public:** price, quantity, currency, trading and reporting time, latency against the one-minute
  limit. These are the RTS 1 Table 3 post-trade fields, which never identify the counterparties.

## Before you start

On the droplet (or wherever the stack runs), from `fixflux/`:

```bash
ssh -i ~/.ssh/fixflux_do root@<droplet-ip>
cd ~/python-engineering-lab/fixflux

# The pipeline and reporting-service must be up
docker compose ps reporting-service matching-engine risk-service order-service compliance-api

# The demo symbols' order books should be empty, or the demo orders may match
# leftover orders instead of each other. Every line printed should end in 0.0.
curl -s localhost:8003/metrics | grep -E '^orders_in_book\{.*symbol="(AAPL|MSFT|EURUSD)"'
```

If a book isn't empty, run `scripts/cleanup.sh` first.

To open the injector from your laptop without exposing a port, tunnel it:

```bash
ssh -i ~/.ssh/fixflux_do -L 8010:localhost:8010 root@<droplet-ip>
# then browse to http://localhost:8010/
```

## Step 1: inject the orders

1. Open the FixFlux Console at `http://localhost:8010/`, on the **FIX Msg Injector** tab.
2. Upload `data/mifid_reporting_demo.txt`, or paste its six lines into the text box.
3. Submit. The response should say **6 published**.

The injector publishes to `raw_orders`, the same entry point as the filedrop client. From there the
orders flow through order-service, risk-service and matching-engine, and each trade lands in
`regulatory_reports` within a second or two.

## Step 2: show the results

Run these on the droplet from `fixflux/`. Each query only looks at the demo clients' reports from
the last 10 minutes, so earlier runs and other traffic don't show up.

**Every report: status and why**

```bash
docker compose exec -T postgres psql -U fixuser -d fixdb -c "
SELECT symbol, buyer_client_id AS buyer, seller_client_id AS seller,
       status, coalesce(status_reason, '-') AS reason
  FROM regulatory_reports
 WHERE buyer_client_id IN ('DEMO_BUYER1', 'DEMO_BUYER2', 'VOL_B0001')
   AND reporting_timestamp > now() - interval '10 minutes'
 ORDER BY reporting_timestamp DESC;"
```

**Restricted view: what the regulator gets**

```bash
docker compose exec -T postgres psql -U fixuser -d fixdb -c "
SELECT symbol, buyer_lei, seller_lei,
       buyer_trading_capacity AS buy_cap, seller_trading_capacity AS sell_cap, cfi_code
  FROM regulatory_reports
 WHERE buyer_client_id = 'DEMO_BUYER1' AND status = 'REPORTABLE'
   AND reporting_timestamp > now() - interval '10 minutes';"
```

**Public view: what post-trade transparency publishes**

```bash
docker compose exec -T postgres psql -U fixuser -d fixdb -c "
SELECT trade_id, symbol, price, price_currency, quantity,
       trading_timestamp, reporting_timestamp,
       publication_latency_ms AS latency_ms, deadline_breached
  FROM regulatory_reports
 WHERE buyer_client_id = 'DEMO_BUYER1' AND status = 'REPORTABLE'
   AND reporting_timestamp > now() - interval '10 minutes';"
```

**Grafana dashboard:** open **FIXFlux - MiFID II Post-Trade Reporting** in Grafana (port 3000).
After the injection it shows one each of reportable / not reportable / incomplete, zero deadline
breaches, and the latency curve well under the 60s line. The **Latest reports** table at the
bottom lists each report's public RTS 1 fields: trade, symbol, price, quantity, times, status and
latency. It never shows LEIs, client IDs or trading capacity, and the reason for `INCOMPLETE`
reports is redacted, because it names the client. Set the time range to cover your injection,
e.g. "Last 15 minutes".

The table needs a one-time setup on the host, since its database password is a secret:

```bash
cd ~/python-engineering-lab/fixflux
# Choose a strong password; .env is gitignored and stays on the droplet
echo "GRAFANA_DB_READER_PASSWORD=$(openssl rand -hex 24)" >> .env
docker compose --profile full --profile monitoring up -d reporting-service grafana
docker compose logs reporting-service | grep grafana_reader   # "grafana_reader role ready"
```

If the table shows an authentication error, that step hasn't been done. Everything else on the
dashboard works without it.

**Metrics** (port 8012 isn't published to the host, so read it from inside the container):

```bash
docker compose exec -T reporting-service python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8012/metrics').read().decode())" \
  | grep -E '^regulatory_reports_total|^regulatory_report_latency_seconds_(count|sum)'
```

### Example output

Illustrative. Trade IDs, timestamps and latency differ on every run. The LEIs are fixed, since they
come from `services/reporting-service/reference/reference_data.yaml`.

```
 symbol |    buyer    |    seller    |     status     |                         reason
--------+-------------+--------------+----------------+----------------------------------------------------------------------
 MSFT   | VOL_B0001   | TRADER2      | INCOMPLETE     | no LEI for buyer VOL_B0001
 EURUSD | DEMO_BUYER2 | DEMO_SELLER2 | NOT_REPORTABLE | FX spot is treated as outside MiFID II transparency in this simulator
 AAPL   | DEMO_BUYER1 | DEMO_SELLER1 | REPORTABLE     | -

 symbol |      buyer_lei       |      seller_lei      | buy_cap | sell_cap | cfi_code
--------+----------------------+----------------------+---------+----------+----------
 AAPL   | SIMX00NJHVVLJWTTIT90 | SIMX00GC5J8027LHE208 | DEAL    | DEAL     | ESVUFR
```

## Optional step 3: idempotency

Redeliver the AAPL trade to the `trades` topic, exactly as Kafka would after a consumer restart, and
show it still has one row:

```bash
docker compose exec -T postgres psql -U fixuser -d fixdb -tA -c "
SELECT json_build_object(
         'trade_id', trade_id, 'symbol', symbol,
         'buy_order_id', 'DUP', 'sell_order_id', 'DUP',
         'price', price, 'quantity', quantity,
         'buy_client_id', buyer_client_id, 'sell_client_id', seller_client_id,
         'timestamp', trading_timestamp)
  FROM regulatory_reports
 WHERE buyer_client_id = 'DEMO_BUYER1' AND status = 'REPORTABLE'
 ORDER BY reporting_timestamp DESC LIMIT 1;" \
  | docker compose exec -T redpanda rpk topic produce trades

sleep 3
docker compose logs --since 30s reporting-service | grep 'status=DUPLICATE'
```

The log line shows `status=DUPLICATE`, and rerunning the first query still shows one AAPL row.
`trade-store-consumer` also logs a duplicate-key error for this message. That's expected: the trade
is already stored there too.

## Talking points

1. **One record per trade, always.** Out-of-scope and incomplete trades are stored too, with the
   reason. Nothing is silently dropped, and missing reference data is flagged, not defaulted.
2. **Two regimes, one table.** The public report (RTS 1) and the regulator's report (RTS 22) need
   different fields. The public one must not reveal who traded.
3. **Real formats.** LEIs are 20 characters with ISO 7064 check digits, CFI codes are 6
   characters, and capacity is `DEAL`/`MTCH`/`AOTC`. Every LEI here is synthetic (prefix `SIMX00`).
4. **The one-minute rule.** `publication_latency_ms` and `deadline_breached` measure each report
   against RTS 1 Art. 14's "within one minute". The latency histogram has a bucket at exactly 60s,
   so breaches can be counted exactly.
5. **Idempotent under redelivery.** A unique constraint on `trade_id` plus `ON CONFLICT DO NOTHING`.

## Running the demo more than once

The injector sends client IDs as written, so every run reuses `DEMO_BUYER1` etc.

- **Use the time window.** The queries above filter on the last 10 minutes. Wait that long between
  runs, or shorten the interval, or earlier runs' rows will appear too.
- **Positions build up in risk-service.** Each run adds 1,000 EURUSD to DEMO_BUYER2's position.
  Given `RISK_NET_POSITION_LIMIT=5000` in `docker-compose.yml`, expect the EURUSD order to be
  rejected from about the 6th run until risk-service restarts
  (`docker compose restart risk-service`). This is inferred from the configured limits, not
  observed.

## If something goes wrong

| Symptom | Cause / fix |
|---|---|
| Fewer than 3 rows | risk-service rejected an order: the fat-finger check against a very different last trade price, or the position limit above. Check `docker compose logs --since 5m risk-service \| grep REJECTED`. |
| A trade involves a client not in the demo | A demo order matched a leftover resting order. Run `scripts/cleanup.sh` and inject again. |
| No rows at all | Check `docker compose logs --since 5m reporting-service`, and that the injector reported 6 published. |
| Injector page doesn't load | Is the SSH tunnel open? Is `compliance-api` running? |

## Side effects

Each run adds three rows to `regulatory_reports` and three trades to `trades`. `cleanup.sh`
deliberately does not delete regulatory reports.
