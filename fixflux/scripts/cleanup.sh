#!/usr/bin/env bash
# Reclaims disk space on the DigitalOcean Droplet.
# Deletes stale PostgreSQL records, dangling Docker images, builder cache,
# and CI test artifacts. Safe to run against a live stack.
#
# Usage: RETAIN_DAYS=30 bash cleanup.sh
#        (defaults to 30 days if RETAIN_DAYS is unset)

set -euo pipefail

RETAIN_DAYS=${RETAIN_DAYS:-30}
REPO_DIR=${REPO_DIR:-$HOME/python-engineering-lab/fixflux}

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[cleanup]${NC} $*"; }
warn() { echo -e "${YELLOW}[cleanup WARN]${NC} $*"; }
err()  { echo -e "${RED}[cleanup ERROR]${NC} $*" >&2; }

echo -e "\n${BOLD}FIXFlux Disk Cleanup${NC} — retaining last ${RETAIN_DAYS} days\n"
echo "Repository: $REPO_DIR"
echo "Started at: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo

# ── Disk usage before ─────────────────────────────────────────────────────────
echo -e "${BOLD}Disk usage before:${NC}"
df -h /
echo

# ── PostgreSQL ────────────────────────────────────────────────────────────────
log "Cleaning PostgreSQL records older than ${RETAIN_DAYS} days..."

if ! docker compose -f "$REPO_DIR/docker-compose.yml" ps postgres --quiet 2>/dev/null | grep -q .; then
    warn "postgres container is not running — skipping DB cleanup"
else
    pg() {
        docker compose -f "$REPO_DIR/docker-compose.yml" \
            exec -T postgres \
            psql -U fixuser -d fixdb -t -c "$1"
    }

    result=$(pg "DELETE FROM trades WHERE timestamp < NOW() - INTERVAL '${RETAIN_DAYS} days';" 2>&1) \
        && log "  trades: $result" \
        || warn "  trades cleanup failed: $result"

    result=$(pg "DELETE FROM compliance_violations WHERE detected_at < NOW() - INTERVAL '${RETAIN_DAYS} days';" 2>&1) \
        && log "  compliance_violations: $result" \
        || warn "  compliance_violations cleanup failed: $result"

    result=$(pg "DELETE FROM compliance_audit_trail WHERE recorded_at < NOW() - INTERVAL '${RETAIN_DAYS} days';" 2>&1) \
        && log "  compliance_audit_trail: $result" \
        || warn "  compliance_audit_trail cleanup failed: $result"

    # client_risk_scores is a stateful per-client view — do not delete by time
    log "  client_risk_scores: skipped (stateful, not time-series)"
fi

# ── Docker images ─────────────────────────────────────────────────────────────
log "Pruning dangling Docker images..."
docker image prune -f

log "Pruning Docker builder cache..."
docker builder prune -f

# ── CI test artifacts ─────────────────────────────────────────────────────────
log "Removing /tmp CI test reports..."
if [[ -d /tmp/fixflux-reports ]]; then
    rm -rf /tmp/fixflux-reports
    log "  /tmp/fixflux-reports removed"
else
    log "  /tmp/fixflux-reports not found, nothing to remove"
fi

# Remove any leftover JUnit XML files in /tmp older than 7 days
find /tmp -maxdepth 2 -name "*.xml" -mtime +7 -delete 2>/dev/null \
    && log "  stale JUnit XML files removed" || true

# ── Processed FIX files ───────────────────────────────────────────────────────
FILEDROP="$REPO_DIR/clients/fix-filedrop-client/filedrop"

for subdir in processed rejected; do
    dir="$FILEDROP/$subdir"
    if [[ -d "$dir" ]]; then
        count=$(find "$dir" -type f -mtime +"$RETAIN_DAYS" | wc -l)
        if [[ $count -gt 0 ]]; then
            find "$dir" -type f -mtime +"$RETAIN_DAYS" -delete
            log "  filedrop/$subdir: removed $count files older than ${RETAIN_DAYS} days"
        else
            log "  filedrop/$subdir: nothing to remove"
        fi
    fi
done

# ── Disk usage after ──────────────────────────────────────────────────────────
echo
echo -e "${BOLD}Disk usage after:${NC}"
df -h /
echo
echo -e "${GREEN}${BOLD}Cleanup complete.${NC} $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
