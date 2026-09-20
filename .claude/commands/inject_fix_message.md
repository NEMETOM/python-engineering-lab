Help the user inject and debug raw FIX New Order Single (35=D) messages through FixFlux's real
injection path: $ARGUMENTS

### Where this actually lives

There is no separate "injection engine" service. FIX injection is one tab of the FixFlux Console,
served by `compliance-api` (merged there from a formerly-standalone `fix-injector` service — see
git history if you need the "why"):

- Parser: `fixflux/services/compliance-service/src/compliance_service/fix_parser.py` —
  `parse_new_order_single(raw: str) -> dict`. Auto-detects SOH (`\x01`) vs pipe (`|`) delimiter.
  Only `35=D` (New Order Single) is accepted; anything else raises `FixParseError`.
- Producer: `injector_producer.py` — publishes to the `raw_orders` topic via the same shared
  `kafka_client.create_producer()` factory every other service uses. Target topic is overridable
  via `FIX_INJECTOR_TARGET_TOPIC` (defaults to `raw_orders`).
- Route: `api/routes/injector.py` — `GET /` (the UI) and `POST /api/orders/inject` (accepts either
  a `raw_text` form field with one FIX line per row, or an uploaded file — same parsing path
  either way).
- UI: `templates/index.html`, extending the shared `_shell.html` nav (the other tab is
  `/admin/compliance`).

### Minimal valid New Order Single

```
8=FIX.4.2|35=D|49=<CLIENT_ID>|55=<SYMBOL>|54=<1=BUY|2=SELL>|40=2|44=<PRICE>|38=<QTY>|
```

Required tags: `35` (msg type, must be `D`), `55` (symbol), `54` (side), `44` (price), `38`
(quantity). `49` (client ID) defaults to `"UNKNOWN"` if omitted — omitting it entirely is different
from sending `49=` (empty): the latter parses to a falsy client_id and trips
`MissingClientIdRule` in compliance-service; the former does not.

### Constraints that will silently affect whether an order matches (check the live droplet, don't guess)

Before handing the user a "here's a crossing pair" example, check current state rather than assume
prices are safe — this codebase's risk-service and matching-engine are long-lived processes with
in-memory state that persists across every test run, not per-scenario isolated state:

- **Notional cap**: `price * quantity` must be ≤ `RISK_NOTIONAL_LIMIT` (1,000,000 by default).
- **Fat-finger check**: if risk-service already has a last-traded price for that symbol in memory
  (it only resets on container restart), a new order more than `RISK_FAT_FINGER_PCT` (10% default)
  away from it gets rejected before ever reaching the matching engine. Query the live reference
  price first if you're not sure:
  ```bash
  ssh -i ~/.ssh/fixflux_do root@<droplet-ip> \
    "curl -s 'http://localhost:9090/api/v1/query?query=order_matching_latency_seconds_bucket'"
  # or, more directly, query Postgres for the last trade per symbol:
  docker compose exec postgres psql -U fixuser -d fixdb \
    -c "SELECT DISTINCT ON (symbol) symbol, price, timestamp FROM trades ORDER BY symbol, timestamp DESC;"
  ```
- **Open-order cap**: `RISK_MAX_OPEN_ORDERS` (10 default) per `client_id`. Bulk-testing multiple
  orders from the same reused client ID is the single most common way to accidentally produce zero
  trades — give every order its own unique client ID (`VOL_B0001`, `VOL_B0002`, ... — see
  `fixflux/data/matching_trd_volume_1000.txt` for the established convention).
- **Matching-engine's order book is a long-lived, in-memory, per-symbol singleton.** A resting
  order from a session hours or days ago can still be sitting there and will match against a
  "fresh" order in a way that looks surprising if you assume a clean slate. If a clean book is
  actually required, that's what the `reset-pipeline-state.yml` GitHub Actions workflow is for
  (restarts `matching-engine` + `risk-service` — confirm with the user before triggering it, it's
  a real restart of live containers, not a no-op).

### Verifying an injection actually produced a trade

`POST /api/orders/inject` returning `"status": "published"` only confirms the order reached
`raw_orders` — it says nothing about whether it matched. To confirm an actual trade:

```bash
curl http://<droplet-ip>:8000/trades?symbol=<SYMBOL>
```

or check `matching-engine`'s logs for a `trade executed Trade(...)` line, or the
`trades_executed_total` Prometheus counter for that symbol.
