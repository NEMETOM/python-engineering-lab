Help the user connect to and debug FixFlux's real-time market data WebSocket stream: $ARGUMENTS

### Where this actually lives

`market-data-api` is a standalone service (`fixflux/services/market-data-api/`), separate from
`market-data-service` (which does the Kafka-side caching/change-detection and publishes to the
`market_data` topic — see `system_architecture.md`). `market-data-api` just consumes that topic on
a background thread and rebroadcasts it over a WebSocket:

- Consumer: `src/market_data_api/consumer.py` — `MarketDataConsumer`, one background thread per
  process, validates each message as a `schemas/market_data_event.py::MarketDataEvent` and drops
  anything that fails validation.
- Bridge: `asyncio.run_coroutine_threadsafe(...)` hands each validated event from the sync Kafka
  thread over to the async event loop — this is the one deliberate async exception in the codebase
  (see `coding_standards.md`), not a repo-wide pattern.
- Routes: `api/main.py` — `GET /health` and `WEBSOCKET /ws/market-data`. That's the entire surface;
  there is no REST endpoint to poll a snapshot, only the live stream.

### Port — do not assume 8000

`docker-compose.yml` maps this service's container port 8000 to **host port 8006**
(`"8006:8000"`), not 8000. Port 8000 on the droplet is `trade-store`. Always grep
`docker-compose.yml` for the actual mapping before handing the user a URL — don't assume a service
listens on whatever port name intuition suggests.

### Swagger will not show you the stream

`/docs` (FastAPI's auto-generated Swagger UI) only documents HTTP operations from the OpenAPI
schema. A `@app.websocket(...)` route is a different protocol and is invisible to OpenAPI — visiting
`http://<host>:8006/docs` will only ever show `/health`. This is not a bug to fix; it's how FastAPI
and the OpenAPI spec work. To see the actual data, use a real WebSocket client:

**Postman** — supported natively: `New` → `WebSocket`, connect to `ws://<host>:8006/ws/market-data`.
No message needs to be sent; the server only reads (`websocket.receive_text()`) to detect
disconnects and pushes data on its own. See
[Postman's WebSocket docs](https://learning.postman.com/docs/use/send-requests/protocols/websocket/websocket-overview)
if the user hasn't used this Postman feature before.

**Browser devtools console**:
```js
const ws = new WebSocket("ws://<host>:8006/ws/market-data");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

**CLI** (if `websocat` is available):
```bash
websocat ws://<host>:8006/ws/market-data
```

### Connection hangs / times out (not rejected — just hangs)

If a WebSocket client reports a raw connect timeout (e.g. Postman's `Error: connect ETIMEDOUT
<ip>:8006`) rather than a handshake-level rejection, that's a strong signal the packet never
reached the container at all — check the DigitalOcean Cloud Firewall before assuming the app or
client is broken:

1. Rule out the app first (cheap, no auth needed beyond SSH): SSH to the droplet and confirm the
   container is up and answering locally —
   ```bash
   ssh -i ~/.ssh/fixflux_do root@<droplet-ip> \
     "docker compose -f ~/python-engineering-lab/fixflux/docker-compose.yml ps market-data-api && curl -sS http://localhost:8006/health"
   ```
   If that returns `{"status": "ok", ...}`, the app is fine and the problem is purely network-path —
   don't waste time re-checking the client or the code.
2. Check the Cloud Firewall's inbound rules (firewall ID `e68d6b13-1221-4a99-ab43-5ae756b19891`):
   ```bash
   doctl compute firewall get e68d6b13-1221-4a99-ab43-5ae756b19891 --format InboundRules
   ```
   As of 2026-09-20 this firewall only allows `22, 3000, 8000, 8010` publicly and `8020` restricted
   to one IP — a service added after the firewall was last updated (like `market-data-api` on 8006)
   will silently time out until its port is added. This is a recurring pattern, not a one-off: any
   *new* service's host port needs an explicit rule added, deployment doesn't do this automatically.
3. Add the missing rule (match the existing pattern — public, like the other app-facing ports,
   unless the user wants it IP-restricted):
   ```bash
   doctl compute firewall add-rules e68d6b13-1221-4a99-ab43-5ae756b19891 \
     --inbound-rules "protocol:tcp,ports:<PORT>,address:0.0.0.0/0"
   ```

**If `doctl` itself fails before you get this far**: a 401 on every command means no valid token is
configured (`doctl auth list` still shows a context, but that doesn't mean the token in it works).
Generate a fresh Personal Access Token (not an OAuth client secret) at
`cloud.digitalocean.com/account/api/tokens`, then run `doctl auth init` **interactively** (no `-t
<token>` flag) so the token is never typed as a literal argument or pasted into chat/logs — treat
any token that does end up in plaintext anywhere (terminal history, chat, a file) as compromised
and revoke it immediately, even if it was your own mistake and nothing else has gone wrong.

### What you'll actually see

One JSON object per symbol, published only when something changes (not on a fixed interval) —
matches `MarketDataEvent` in `schemas/market_data_event.py`:

```json
{
  "symbol": "EURUSD",
  "best_bid": 1.0899,
  "best_ask": 1.0901,
  "mid_price": 1.0900,
  "last_trade_price": 1.0900,
  "timestamp": "2026-09-20T12:34:56.789000"
}
```

If nothing shows up after connecting, that's very likely because no trade or order book change has
happened since the connection opened — not a broken feed. Inject an order via the FixFlux Console
(see `inject_fix_message.md`) or drop a matching pair through the filedrop client to generate an
event, and check the client actually connected (server logs a connect/disconnect per
`ConnectionManager`) before assuming the stream itself is broken.

### "I injected a crossing pair and got nothing" — verified diagnostic chain (2026-09-20)

This happened for real during a demo and is *not* a bug — it's the "publish only on change"
behavior working correctly, catching people because it's easy to accidentally submit a trade that
doesn't actually change the cached market state. Walk the pipeline hop by hop rather than guessing
which layer is broken — each step is cheap and rules out one whole service:

1. **Did the trade even happen?**
   ```bash
   curl "http://<host>:8000/trades?symbol=<SYMBOL>"
   ```
   If your trade isn't there, the problem is upstream of market data entirely (risk rejection, no
   crossing counterpart, stale in-memory reference price — see `inject_fix_message.md`). Stop here.

2. **Is `market-data-service` actually caught up on the topics it consumes?**
   ```bash
   ssh -i ~/.ssh/fixflux_do root@<droplet-ip> \
     "docker compose -f ~/python-engineering-lab/fixflux/docker-compose.yml exec -T redpanda rpk group describe market-data-service"
   ```
   Look at `TOTAL-LAG` — if it's `0`, the service has processed your trade even if its logs have
   been silent for days (it only logs at WARNING/ERROR, not per-message, so log silence alone means
   nothing — a consumer that's actually stuck looks identical in the logs to one that's just quiet).

3. **Did it actually publish a new `market_data` message?**
   ```bash
   ssh -i ~/.ssh/fixflux_do root@<droplet-ip> \
     "docker compose -f ~/python-engineering-lab/fixflux/docker-compose.yml exec -T redpanda rpk topic consume market_data -n 5 -o -5"
   ```
   Compare the last message's `timestamp` to when your trade happened. If the last message predates
   your trade, `publisher.py`'s change-detection suppressed it — **check whether your test order
   actually changed `(best_bid, best_ask, last_trade_price)` from the previous cached state.** A
   fully-crossing pair at a price identical to the last trade, when the book was already empty
   before and after, changes *nothing* — same `last_trade_price`, `best_bid`/`best_ask` stay `null`
   either side of a full fill. The fix is trivial: use a **different price** than whatever that
   symbol last traded at, which guarantees a real state change and a real publish. Don't reuse the
   same worked example (e.g. `EURUSD @ 1.09`) across a whole demo/presentation for this reason — vary
   the price each time or you'll get intermittent "nothing happened" moments live.

4. Only if step 3 shows a fresh message with no corresponding WebSocket delivery is the actual bug
   in `market-data-api` itself (check its logs for `client connected` / Kafka errors).
