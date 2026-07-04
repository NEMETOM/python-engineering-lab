#!/usr/bin/env bash
# Smoke-test all three observability pillars: Prometheus metrics, Tempo traces, Grafana datasources.
#
# Usage:
#   ./scripts/check-observability.sh                          # local Docker stack
#   ./scripts/check-observability.sh <droplet-ip>             # remote Droplet
#   DO_DROPLET_IP=x.x.x.x ./scripts/check-observability.sh   # via env var

set -uo pipefail

HOST="${1:-${DO_DROPLET_IP:-}}"
SSH_KEY="${DO_SSH_KEY_PATH:-$HOME/.ssh/fixflux_do}"

check() {
  G="http://admin:admin@localhost:3000"
  P="http://localhost:9090"
  T="http://localhost:3200"
  PASS=0; FAIL=0

  ok()   { echo "  [OK]   $*"; PASS=$((PASS + 1)); }
  fail() { echo "  [FAIL] $*"; FAIL=$((FAIL + 1)); }

  echo ""
  echo "=== Grafana (10.x) ==="
  curl -sf "$G/api/health" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('  db:', d['database'], '| version:', d['version'])" \
    && ok "Grafana up" || fail "Grafana unreachable"

  curl -sf "$G/api/datasources/uid/prometheus/health" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Prometheus datasource:', d['status'], d.get('message',''))" \
    && ok "Prometheus datasource" || fail "Prometheus datasource unreachable"

  curl -sf "$G/api/datasources/uid/tempo/health" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Tempo datasource:', d['status'], d.get('message',''))" \
    && ok "Tempo datasource" || fail "Tempo datasource unreachable"

  echo ""
  echo "=== Prometheus (direct) ==="
  curl -sf "$P/-/ready" > /dev/null && ok "Prometheus ready" || fail "Prometheus not ready"

  SERIES=$(curl -sf "$P/api/v1/query?query=kafka_messages_consumed_total" \
    | python3 -c "import sys,json; print(len(json.load(sys.stdin)['data']['result']))" 2>/dev/null || echo 0)
  [ "$SERIES" -gt 0 ] \
    && ok "kafka_messages_consumed_total: $SERIES series" \
    || fail "kafka_messages_consumed_total: no data (services not scraping yet?)"

  echo ""
  echo "=== Tempo (direct) ==="
  curl -sf "$T/ready" > /dev/null && ok "Tempo ready" || fail "Tempo not ready"

  TRACES=$(curl -sf "$T/api/search?limit=5" \
    | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('traces', [])))" 2>/dev/null || echo 0)
  [ "$TRACES" -gt 0 ] \
    && ok "Recent traces: $TRACES (run e2e to populate)" \
    || fail "No recent traces (run e2e tests first, or OTel not yet deployed)"

  echo ""
  echo "=== Summary: $PASS passed, $FAIL failed ==="
  [ "$FAIL" -eq 0 ]
}

if [ -z "$HOST" ]; then
  echo "Checking local Docker stack..."
  check
else
  echo "Checking $HOST..."
  ssh -i "$SSH_KEY" "root@$HOST" "$(declare -f check); check"
fi
