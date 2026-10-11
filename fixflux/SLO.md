# FixFlux — Service Level Objectives

Formal SLI/SLO definitions and the error-budget burn-rate alerting built on top of
them. This exists so "is trade-store healthy" has a precise, agreed-upon
answer instead of an informal "dashboards look fine" judgment call — the
stated prerequisite for a meaningful on-call escalation policy or a
production-readiness review.

## Scope: trade-store only, for now

**`trade-store` is the only service in this stack with real per-request HTTP
metrics today.** Verified by reading the actual middleware code, not assumed:

- `trade-store`'s `_PrometheusMiddleware` (`services/trade-store/src/trade_store/api/main.py`)
  genuinely records `api_requests_total{endpoint,method,status_code}` and
  `api_request_latency_seconds{endpoint}` on every request.
- `compliance-api`'s `_MetricsMiddleware` (`services/compliance-service/src/compliance_service/api/main.py`)
  only does `logger.debug()` timing — it never touches a Prometheus Counter or
  Histogram. There is currently no HTTP-level metric to build an SLI on for
  that service.

So every SLI below is scoped to `trade-store`. Extending this to
`compliance-api` is real follow-up work (wire its middleware the same way
trade-store's is), not something this document can define yet without
fabricating a metric that doesn't exist.

## A prerequisite fix this work required

Before any SLI could be trusted, one real bug had to be fixed: the
middleware was labeling both metrics with `request.url.path` — the **raw**
URL (e.g. `/trades/T1`, `/trades/T2`, ...) rather than the **route template**
(`/trades/{trade_id}`). Every unique `trade_id` ever queried was creating a
brand-new time series, forever — unbounded cardinality on a metric meant to
be a small, fixed set of endpoints. Fixed to use `request.scope["route"].path`
(the matched route template, available once routing has resolved), falling
back to the raw path only for genuinely unmatched routes (404s). Building
burn-rate math on top of an unbounded-cardinality label would have been
building on a foundation that was already quietly breaking.

## SLI 1 — Latency

**Definition:** the proportion of `trade-store` HTTP requests that complete
in under 200ms.

**Why 200ms specifically:** it's a real bucket boundary in
`api_request_latency_seconds` (`shared/observability/metrics.py`), added
deliberately for this. Burn-rate math needs the SLI to be an exact ratio of
real event counts — `histogram_quantile()`'s linear interpolation across a
bucket gap is an estimate, not a count, and isn't precise enough for the "is
the error budget actually being consumed" question an alert has to answer
correctly.

```promql
# "good" = requests with latency <= 0.2s
sum(rate(api_request_latency_seconds_bucket{job="trade-store", le="0.2"}[<window>]))
/
sum(rate(api_request_latency_seconds_count{job="trade-store"}[<window>]))
```

**SLO target:** 99.9% over a rolling 30-day window.

## SLI 2 — Availability

**Definition:** the proportion of `trade-store` HTTP requests that do **not**
return a 5xx status code.

```promql
sum(rate(api_requests_total{job="trade-store", status_code!~"5.."}[<window>]))
/
sum(rate(api_requests_total{job="trade-store"}[<window>]))
```

**SLO target:** 99.9% over a rolling 30-day window.

## Error budget

A 99.9% SLO over 30 days allows a 0.1% "bad event" ratio. In time terms, if
the service were down/slow 100% of the time it would exhaust that budget in:

```
0.1% of 30 days = 0.001 x 30 x 24 x 60 minutes = 43.2 minutes
```

That's the entire monthly error budget per SLI, not an alert threshold by
itself — the budget is what the burn-rate alerts below are measuring
consumption *against*.

## Burn-rate alerting

Implemented in `infrastructure/monitoring/prometheus_slo_rules.yml`, following
Google's SRE Workbook chapter "Alerting on SLOs" — specifically its
recommended multiwindow, multi-burn-rate table (Table 5-8), fetched and
verified directly against <https://sre.google/workbook/alerting-on-slos/>
rather than reconstructed from memory:

| Severity | Long window | Short window | Burn rate | Budget consumed by the time it fires |
|---|---|---|---|---|
| Page | 1 hour | 5 minutes | 14.4x | 2% |
| Page | 6 hours | 30 minutes | 6x | 5% |
| Ticket | 3 days | 6 hours | 1x | 10% |

This table has **3 rows**, not the 4-row version sometimes quoted elsewhere —
that confusion comes from a worked PromQL example earlier in the same
chapter that includes an extra 24h/2h/3x condition which the book's own
final recommended table drops. Implemented exactly as the real 3-row table.

For a 99.9% SLO (error budget = 0.001), each tier's alert threshold is
`burn_rate x 0.001`:

- Page (14.4x): fires above **1.44%** bad-event ratio
- Page (6x): fires above **0.6%** bad-event ratio
- Ticket (1x): fires above **0.1%** bad-event ratio

Each tier requires **both** its long and short window to independently
exceed the threshold (an `and` of two recorded ratios) before firing — this
is what makes it "multiwindow": a short-window-only check would page on a
30-second blip, and a long-window-only check would take hours to notice a
real outage. Applied identically to both the latency and availability SLIs,
giving 4 alert rules total: `TradeStoreLatencySLOBurnRatePage`,
`TradeStoreLatencySLOBurnRateTicket`, `TradeStoreAvailabilitySLOBurnRatePage`,
`TradeStoreAvailabilitySLOBurnRateTicket`.

**These alerts route through the same Alertmanager as the existing
threshold-based alerts in `prometheus_alerts.yml`.** `alertmanager.yml`'s
routing tree now has dedicated `page`/`ticket` routes alongside the existing
`critical`/`warning` ones (Google's own terminology, used as-is rather than
force-fit onto the threshold-alert scheme) — but, same as `critical` and
`warning`, neither `page` nor `ticket` has a real Slack/email/PagerDuty
receiver configured. Fired alerts are visible at `:9093`; nothing pages
anyone yet.

## A second prerequisite fix: retention didn't cover the SLO window

Prometheus was configured with `--storage.tsdb.retention.time=15d`
(`docker-compose.yml`) — less than the 30-day SLO window this document
defines. A genuine 30-day error-budget-consumption query would have silently
returned incomplete data once anything older than 15 days aged out, with no
error to indicate it was wrong. Bumped to `30d` to actually cover the period
being measured. None of the burn-rate *alerts* in `prometheus_slo_rules.yml`
were affected by this (their longest window is 3 days, well inside even the
old 15-day retention) — only a genuine full-period budget view would have
been silently wrong.

## Grafana dashboard

`infrastructure/monitoring/grafana/dashboards/slo_overview.json` — current
SLI value, remaining 30-day error budget, and the burn-rate time series for
both windows per SLI, so a burn-rate alert firing can be visually confirmed
rather than taken on faith.

## Follow-up work this surfaces (not implemented here)

- **No real notification channel for any severity** - `default`, `critical`,
  `warning`, `page`, and `ticket` are all structural placeholders in
  `alertmanager.yml` until a real Slack webhook, email SMTP config, or
  PagerDuty key is added. This is the actual blocker on a meaningful on-call
  escalation policy, not the routing tree (which is now complete).
- **compliance-api has no SLI** until its `_MetricsMiddleware` is wired to
  real Counters/Histograms the way trade-store's is.
- **OPERATIONS.md runbooks** (a separate item in the FixFlux README's Future
  Improvements table) is the natural next step once these alerts can
  actually page someone — a burn-rate alert firing needs a documented
  "what do I do now" on the other end of it.
