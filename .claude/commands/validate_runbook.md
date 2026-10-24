Validate `fixflux/OPERATIONS.md` against the live FixFlux droplet, acting as the SRE persona: $ARGUMENTS

`$ARGUMENTS` is optional: a section number (`2`, `3`, `4`) or alert name (`KafkaConsumerLagHigh`,
`MatchingEngineDown`) to limit the run. Empty means all sections.

### Setup

1. Read `.claude/agents/sre_agent.md` in full and adopt its persona, ground-truths and diagnostic
   method for this task (same as the `sre-agent` skill).
2. Read `.claude/instructions/system_architecture.md` and `fixflux/OPERATIONS.md`.
3. Droplet access is in `fixflux/DROPLET_ACCESS.md`. Run every remote command as
   `ssh -i ~/.ssh/fixflux_do root@<droplet-ip> '<command>'` from `~/python-engineering-lab/fixflux`.

### Hard rule: read-only

This validates the runbook; it is not an incident. **Do not run anything that changes state** -
no `docker compose restart/stop/start/up/down/scale`, no `rpk group seek`, no `pg_terminate_backend`,
no `curl -X POST .../-/reload`, no `git checkout`, no file writes on the droplet. For every
state-changing command in the runbook, validate it **without executing it**:

- `rpk ...`: run `rpk <subcommand> --help` in the `redpanda` container and confirm every flag the
  runbook uses exists (in particular `rpk group seek --to-file`, `--to start|end`, `--topics`, and
  `rpk cluster logdirs describe`).
- `docker compose ...`: confirm the service names exist in `docker compose config --services`.
- If a command can't be validated without running it, mark it UNVERIFIED and say why.

If anything would need a state change to verify, stop and ask the user first.

### What to check

For each runbook command in scope:
1. **Read-only diagnostics** (`dc ps`, `docker inspect`, `docker stats --no-stream`, `rpk group
   describe`, `rpk topic describe`, `rpk cluster health`, Prometheus/Alertmanager `curl` GETs,
   `psql` SELECTs): run them and confirm they succeed and their output matches what the runbook
   says to look for (column names like `CURRENT-OFFSET`/`STATE`, label names, metric names).
2. **Facts the runbook asserts**: consumer group names (section 1.3), partition counts on every
   topic, topic retention on `risk_approved_orders`, `up{job="matching-engine"}`, that
   `MatchingEngineDown` and both `runbook_url` annotations are loaded
   (`curl -s localhost:9090/api/v1/rules`), and that the GitHub anchor links resolve.
3. **Drift**: anything in the repo (compose, alert rules, consumer code) that no longer matches
   the runbook.

### Output

A table per section: `Command / claim | Result (PASS / FAIL / UNVERIFIED) | Evidence`, with the
exact command output that justifies each verdict (trimmed to the relevant lines). Then a list of
proposed `OPERATIONS.md` edits for every FAIL. **Do not apply them** - show them as diffs and wait
for the user's go-ahead.
