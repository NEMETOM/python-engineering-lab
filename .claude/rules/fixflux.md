---
paths:
  - "fixflux/**"
---

# Working in fixflux

Before making a change here, read `.claude/instructions/system_architecture.md` and
`.claude/instructions/coding_standards.md` if you haven't already this session — they describe the
real, verified architecture (topic flow, service layout, sync-vs-async split, HTTP surfaces) and
this repo's actual testing/lint conventions, not an idealized target.

A pasted spec or enhancement prompt that assumes Hexagonal Architecture, DDD, `aiokafka`, or
testcontainers is describing a different codebase than this one — flag the mismatch to the user
before implementing, don't silently follow the spec verbatim. This has happened repeatedly with
real pasted prompts in this project; treat it as the default case to check for, not an edge case.

This is a simulator/portfolio project, not a production trading venue — proposals should stay
proportionate to a single 2 vCPU / 4GB DigitalOcean droplet (see
`.claude/skills/predeploy-check/` before pushing a change to `docker-compose.yml` or
`infrastructure/monitoring/`).

## Droplet security baseline (keep it this way)

Hardened 2026-10-25 at the repo owner's request. FixFlux holds no sensitive data, but the
committed `fixuser`/`fixpass` credentials and a public Grafana made the data easy to tamper
with. Don't regress any of these:

- **Postgres is loopback-only:** `127.0.0.1:5433:5432` in `docker-compose.yml`. Never publish it
  on all interfaces; use `ssh -L 5433:localhost:5433` for remote access.
- **Grafana's Postgres datasource uses `grafana_reader`, never `fixuser`.** That role can only
  `SELECT` from `regulatory_reports_public` (no LEIs or client IDs). It runs read-only
  transactions, with a 5s statement timeout and a 3-connection limit (set in
  `reporting_service/public_view.py`, re-applied on every start).
- **reporting-api's feed uses `public_feed_reader`, never `fixuser`.** Same restrictions as
  `grafana_reader` (view only, read-only, 5s timeout, 3 connections). It's published as
  `127.0.0.1:8013`. The owner chose to keep it loopback-only (2026-11-22) after the Grafana
  incident below, even though the data is public by design. Don't drop the prefix unless asked.
- **Secrets live in `fixflux/.env` on the host** (gitignored): `GRAFANA_DB_READER_PASSWORD`,
  `PUBLIC_FEED_DB_READER_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`. Never commit them, and never add a
  default for either reader password.
- **Grafana:** no anonymous access, and Viewers can't use Explore. The admin password is set
  from `.env` on a fresh volume; rotate a running instance with
  `grafana cli admin reset-admin-password`.
- **Grafana is loopback-only** (`127.0.0.1:3000:3000`); use `ssh -L 3000:localhost:3000`. And
  `GF_SECURITY_ADMIN_PASSWORD` has **no fallback** (`:?`), so compose refuses to run without
  `GRAFANA_ADMIN_PASSWORD`. Never restore `:-admin` or a public 3000. Why: the old `:-admin`
  default left admin/admin on public :3000 from 2026-11-01. On 2026-11-16, 193.187.110.182 used
  it to create admin `hxops_89cnx7` and delete `admin`. Evidence is in
  `/root/incident-20261116/` on the droplet. Note that Grafana only logs non-200 requests, so
  successful API calls (user create/delete) leave no request log.
- **Remote Grafana access is tailnet-only, via Tailscale** (since 2026-11-19). From the owner's
  devices (laptop, iPhone), browse to `http://fixflux-prod:3000`. On the droplet,
  `tailscale serve --bg --http=3000 http://127.0.0.1:3000` forwards the tailnet to the loopback
  port. It persists across reboots and deploys, and it's outside compose; check it with
  `tailscale serve status`. Keep the compose binding at `127.0.0.1`. Never bind Grafana to the
  tailnet IP in compose (Docker can start before `tailscaled` has the address) or to `0.0.0.0`.
  The SSH tunnel still works as a fallback.

Still published on all interfaces (Redpanda 9092, compliance-api 8010, Prometheus 9090 and
others): check the `ports:` entries in `docker-compose.yml` before assuming a port is private.
Only a `127.0.0.1:` prefix makes it loopback-only.
