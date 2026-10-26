#!/usr/bin/env bash
# Demo: MiFID II post-trade reporting end to end.
#
# Replays data/mifid_reporting_demo.txt (three matching order pairs) through the live
# pipeline with fix-replay, then shows the regulatory_reports rows reporting-service wrote:
#   AAPL   DEMO_BUYER1 / DEMO_SELLER1  -> REPORTABLE      (in scope, both LEIs known)
#   EURUSD DEMO_BUYER2 / DEMO_SELLER2  -> NOT_REPORTABLE  (FX spot out of scope)
#   MSFT   VOL_B0001   / TRADER2       -> INCOMPLETE      (no LEI for VOL_B0001)
#
# Usage (from anywhere; run where the stack runs, e.g. on the droplet):
#   ./scripts/demo-mifid-reporting.sh                    # standard demo
#   ./scripts/demo-mifid-reporting.sh --with-duplicate   # also show idempotency
#   ./scripts/demo-mifid-reporting.sh -- --allow-resting # pass extra args to fix-replay
#
# See scripts/demo-mifid-reporting.md.

set -uo pipefail

cd "$(dirname "$0")/.."   # fixflux/

WITH_DUPLICATE=0
if [[ "${1:-}" == "--with-duplicate" ]]; then WITH_DUPLICATE=1; shift; fi
[[ "${1:-}" == "--" ]] && shift

RUN_ID="mifid$(date +%H%M%S)"   # no hyphens: reporting-service strips ^RPL-[^-]+-
PREFIX="RPL-${RUN_ID}-"
WAIT_SECONDS=30

dc()   { docker compose "$@"; }
psql() { dc exec -T postgres psql -U fixuser -d fixdb -v ON_ERROR_STOP=1 "$@"; }
step() { echo ""; echo "=== $* ==="; }
die()  { echo "ERROR: $*" >&2; exit 1; }

RUN_FILTER="buyer_client_id LIKE '${PREFIX}%' OR seller_client_id LIKE '${PREFIX}%'"

step "1. Pre-flight"
for svc in reporting-service matching-engine risk-service order-service postgres redpanda; do
  dc ps --status running --services 2>/dev/null | grep -qx "$svc" \
    || die "$svc is not running - start the stack first (docker compose --profile full up -d)"
done
echo "  pipeline and reporting-service are running"

step "2. Replay data/mifid_reporting_demo.txt (run id ${RUN_ID})"
dc --profile replay run --rm fix-replay /data/mifid_reporting_demo.txt \
  --run-id "$RUN_ID" --out "/results/${RUN_ID}.json" "$@"
rc=$?
case $rc in
  0) ;;
  3) die "fix-replay pre-flight refused: resting orders already on AAPL/EURUSD/MSFT. Reset the
       pipeline (scripts/cleanup.sh) or rerun with: $0 -- --allow-resting" ;;
  *) die "fix-replay exited $rc (see its log above)" ;;
esac

step "3. Waiting for reporting-service (up to ${WAIT_SECONDS}s)"
rows=0
for _ in $(seq "$WAIT_SECONDS"); do
  rows=$(psql -tA -c "SELECT count(*) FROM regulatory_reports WHERE ${RUN_FILTER};")
  [[ "$rows" -ge 3 ]] && break
  sleep 1
done
echo "  ${rows} report(s) for this run"
[[ "$rows" -ge 1 ]] || die "no reports written - check: docker compose logs --since 5m reporting-service"
[[ "$rows" -ge 3 ]] || echo "  (expected 3: a trade may have been rejected by risk-service - see the fix-replay summary above)"

step "4. Every report: status and why"
psql -c "
SELECT symbol,
       replace(buyer_client_id,  '${PREFIX}', '') AS buyer,
       replace(seller_client_id, '${PREFIX}', '') AS seller,
       status,
       replace(coalesce(status_reason, '-'), '${PREFIX}', '') AS reason
  FROM regulatory_reports WHERE ${RUN_FILTER} ORDER BY symbol;"

step "5. Restricted view (RTS 22-style, for the regulator only)"
psql -c "
SELECT symbol, buyer_lei, seller_lei,
       buyer_trading_capacity AS buy_cap, seller_trading_capacity AS sell_cap, cfi_code
  FROM regulatory_reports WHERE (${RUN_FILTER}) AND status = 'REPORTABLE';"

step "6. Public post-trade view (RTS 1 Table 3 fields: no counterparty identity)"
psql -c "
SELECT trade_id, symbol, price, price_currency, quantity,
       trading_timestamp, reporting_timestamp,
       publication_latency_ms AS latency_ms, deadline_breached
  FROM regulatory_reports WHERE (${RUN_FILTER}) AND status = 'REPORTABLE';"

if [[ "$WITH_DUPLICATE" == 1 ]]; then
  step "7. Idempotency: redeliver the AAPL trade to the trades topic"
  dup=$(psql -tA -c "SELECT json_build_object(
      'trade_id', trade_id, 'symbol', symbol, 'buy_order_id', 'DUP', 'sell_order_id', 'DUP',
      'price', price, 'quantity', quantity,
      'buy_client_id', buyer_client_id, 'sell_client_id', seller_client_id,
      'timestamp', trading_timestamp)
    FROM regulatory_reports WHERE (${RUN_FILTER}) AND symbol = 'AAPL' LIMIT 1;")
  [[ -n "$dup" ]] || die "no AAPL report to redeliver"
  echo "$dup" | dc exec -T redpanda rpk topic produce trades >/dev/null
  echo "  redelivered: $dup"
  sleep 3
  psql -c "SELECT trade_id, count(*) AS rows_for_trade FROM regulatory_reports
             WHERE (${RUN_FILTER}) AND symbol = 'AAPL' GROUP BY trade_id;"
  dc logs --since 30s reporting-service 2>/dev/null | grep 'status=DUPLICATE' | tail -1
fi

step "Metrics (reporting-service /metrics)"
dc exec -T reporting-service python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8012/metrics').read().decode())" \
  | grep -E '^regulatory_reports_total|^regulatory_report_latency_seconds_(count|sum)'

echo ""
echo "Done. fix-replay's run report: replay-results/${RUN_ID}.json"
