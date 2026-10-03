# Files fixflux's deploy pipeline actually reads

Verified against the real repo (2026-09-27), not assumed — re-check if these change.

## `fixflux/docker-compose.yml` bind mounts (fail silently if source is missing/untracked)

- `./infrastructure/monitoring/prometheus.yml` → `/etc/prometheus/prometheus.yml`
- `./infrastructure/monitoring/prometheus_alerts.yml` → `/etc/prometheus/prometheus_alerts.yml`
  (the one that actually broke — added by a docker-compose.yml edit without the file itself
  being committed in the same change)
- `./infrastructure/monitoring/alertmanager.yml` → `/etc/alertmanager/alertmanager.yml`
- `./infrastructure/monitoring/loki-config.yaml`, `./infrastructure/monitoring/promtail-config.yaml`
- `./infrastructure/monitoring/loki-rules` (directory)
- `./infrastructure/monitoring/tempo.yaml`
- `./infrastructure/monitoring/grafana/provisioning/` and `./infrastructure/monitoring/grafana/dashboards/`
  (whole directories — an individual new dashboard JSON file left untracked would silently just not
  appear, not error)

## `infrastructure/monitoring/prometheus.yml` itself references

- `rule_files: [/etc/prometheus/prometheus_alerts.yml]` — same file as above, now doubly-referenced
- `alerting.alertmanagers` → `alertmanager:9093` (a service name, not a file — no file-tracking risk)
- scrape job targets are service names (`compliance-consumer:8011`, `kafka-exporter:9308`, etc.) —
  these fail loudly (scrape errors visible in Prometheus's own `/targets` page) if a service is
  missing, unlike a silently-directory-ified config file. Lower risk, but still worth a glance.

## k8s / Helm (only relevant if actually deploying that path — currently Docker Compose is the real
deployment target per `.claude/instructions/system_architecture.md`)

- `k8s/02-secret.yaml`, `helm/fixflux/templates/_helpers.tpl` — both hold the `DATABASE_URL` /
  `database-url` connection string; keep in sync with `docker-compose.yml`'s own `DATABASE_URL`
  values (all three were found out of sync with the rest of the repo during the SQLAlchemy 2.1
  `+psycopg2` fix and had to be caught by a manual repo-wide grep, not by CI).

## Quick command to re-run this check for a given change

Tested against this repo (2026-09-27) — no output means everything referenced is tracked; any
`UNTRACKED:` line is exactly the failure mode this skill exists to catch. Uses `sed`, not `grep -P`
— this repo's Git Bash `grep` build rejects `-P` regardless of locale, confirmed by testing both.

```bash
# From fixflux/: list every bind-mount source path docker-compose.yml or prometheus.yml
# references, then confirm each is actually tracked in git
sed -n 's#^\s*- \./\([^:]*\):.*#\1#p' docker-compose.yml infrastructure/monitoring/prometheus.yml \
  | sort -u \
  | while read -r f; do git ls-files --error-unmatch "$f" >/dev/null 2>&1 || echo "UNTRACKED: $f"; done
```
