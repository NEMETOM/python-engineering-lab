# What this file is

`CLAUDE.md` is read automatically by Claude Code at the start of every session in this
repo — unlike a plain instructions file sitting elsewhere, you don't need to point Claude at this
one manually. Keep it short: broad, durable facts and pointers, not a place to dump a full
architecture doc (that's what the files it points to are for).

## Monorepo layout

This is a collection of separate, independent Python mini-projects — not one shared codebase:

- **`fixflux/`** — event-driven trading/compliance platform (Kafka, FastAPI, Postgres). The active,
  most-developed project here.
- **`fix-protocol-simulator/`** — an earlier, smaller, standalone FIX protocol simulator (TCP
  server, order book, matching engine). Separate from `fixflux/`, not a dependency of it.
- **`event_stream_risk_detector/`** — real-time transaction risk detection over Kafka.
- **`price-calculator/`** — a simple price calculator demonstrating clean architecture + CI/CD.
- **`pr-compliance-guard/`** — validates PRs against org rules (branch naming, commit hygiene, Jira
  refs), runnable locally or in CI.
- **`MISC-python-scripts/`**, **`Archive/`** — not active projects; don't treat content here as
  representative of current conventions.

## Working in `fixflux/`

Before making changes here, read:
- `.claude/instructions/system_architecture.md` — the real, verified architecture (topic flow,
  service layout, what's sync vs. async, HTTP surfaces).
- `.claude/instructions/coding_standards.md` — testing conventions, Pydantic/dataclass split,
  lint/format config.

Both are written to describe what's actually in the repo, not an idealized target — treat a
mismatch between a pasted spec and these files as a signal to flag the mismatch, not to follow the
spec verbatim.
