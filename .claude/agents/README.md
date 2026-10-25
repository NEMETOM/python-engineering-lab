# Custom agents in this directory

Three persona system-prompts live here, each a `.md` file with YAML frontmatter (`description` +
`tools`) — the real Claude Code custom-subagent format (not `.json`; a `.json` file in this
directory isn't recognized as an agent at all).

| File | Persona | Use for |
|---|---|---|
| `sdet_agent.md` | Senior SDET | Writing/reviewing pytest & behave suites, enforcing this repo's real testing conventions (mocked Kafka boundary, no testcontainers, 85% coverage gate) |
| `sre_agent.md` | Principal SRE | Diagnosing production behavior, dashboard/alerting work, anything touching the live DigitalOcean droplet |
| `legal_counsel_agent.md` | Legal/forensic audit | Chain-of-custody and tamper-evidence review of the compliance audit trail, mapping technical controls to real regulatory mandates |

Each file documents its own ground rules, verified facts about this codebase, and (in its
frontmatter) the tool access it should actually need — read the file itself for the full picture,
this README only covers *how to invoke* them.

## How to actually invoke one

Verified in this environment (a Claude Code VS Code extension session) as of 2026-10-03: the
`/agents` wizard has been removed, and custom `.claude/agents/*.md` files have **not** been showing
up as selectable types for the Agent/Task tool itself — only built-ins (`Explore`,
`general-purpose`, `Plan`, etc.) appear there. This may differ in a plain CLI session; it hasn't
been tested there. Two things reliably work regardless:

**1. Natural language** — reference the file directly in your prompt:
```
Act as the sre_agent (.claude/agents/sre_agent.md) and check why trades aren't showing up.
```

**2. The skill wrappers in `.claude/skills/`** — a short slash-invocation instead of a full sentence:

`/sdet-agent` — testing tasks (pytest/behave, coverage, mocked Kafka boundary):
```
/sdet-agent write unit tests for the new rule
/sdet-agent review test coverage for risk-service
/sdet-agent debug why the compliance BDD suite is failing
/sdet-agent write a regression test for the rules-engine live-toggle bug
/sdet-agent generate an integration test for market-data-api
```

`/sre-agent` — droplet/observability/deploy-pipeline tasks:
```
/sre-agent check why trades aren't showing up
/sre-agent check whether prometheus_alerts.yml actually loaded on the droplet
/sre-agent diagnose the matching-engine P99 latency spike
/sre-agent check Kafka consumer lag before we push a new consumer service
/sre-agent verify the firewall allows the new service's port before I test it
```

`/legal-counsel-agent` — audit trail, regulatory mapping, forensic replay:
```
/legal-counsel-agent review the audit trail for evidentiary defensibility
/legal-counsel-agent map WashTradingRule to the MiFID II provision it illustrates
/legal-counsel-agent explain the gap between per-record tamper-evidence and true chain-of-custody
/legal-counsel-agent check whether Kafka retention covers replaying a given incident
```

Each skill (`.claude/skills/sdet-agent/`, `sre-agent/`, `legal-counsel-agent/`) is a thin pointer —
its `SKILL.md` just says "read the corresponding agent file and adopt its persona for this task."
The agent `.md` files stay the single source of truth; the skills don't duplicate their content, so
editing an agent file updates what both invocation methods do.

**Important limitation, either way**: both methods run in the *current* conversation with full tool
access — neither is an isolated subagent. The `tools:` list in each agent file's frontmatter is
guidance on what that persona should stick to, not an enforced restriction the way a real subagent
dispatch would apply it. If you need actual tool-access enforcement, that requires the formal
Agent-tool subagent-type mechanism working — which, per the above, isn't currently confirmed to
pick up these custom files in this environment.

---

## Demo playbook: `/sdet-agent` and `/sre-agent`

Prompts for a video demo, each grounded in something that really exists in this repo. Every prompt
is labelled:

- **Read-only:** inspects and reports, changes nothing. Safe to record live.
- **Local edits:** changes files in the working tree, nothing deployed. Review the diff on camera.
- **Changes state:** touches the running stack. The persona should ask before acting; say yes on
  camera so the confirmation step is part of the demo.

Start each segment in a **fresh session**, because both skills run inside the current conversation.
Paste a prompt exactly as written. They're specific on purpose, so the agent has to show evidence,
not describe what it would do.

### `/sdet-agent`: tests, coverage, conventions (all local, no droplet)

**1. Full health check of every suite** (read-only, ~3 min, a good opener)
```
/sdet-agent run the unit tests with coverage and the behave suites for every service under fixflux/services plus fixflux/clients/fix-replay and fixflux/shared. Give me one table: service, tests passed/failed, coverage vs the 85% gate, BDD scenarios passed. Don't fix anything, just report.
```
Shows: the CI gate applied across the whole repo in one pass, with real numbers.

**2. Lint parity with CI** (read-only, ~2 min)
```
/sdet-agent run the exact lint chain CI runs (ruff==0.17.2, black, isort, mypy src/) on every service and on fix-replay. Confirm the local ruff version matches the pin in .github/workflows first. Report any service that would fail CI today.
```
Shows: the "local passes, CI fails" ruff version trap from October 2026, now checked up front.

**3. Contract check on the `trades` topic** (read-only, ~3 min)
```
/sdet-agent matching-engine recently added buy_client_id, sell_client_id and timestamp to the trades payload. Find every consumer of the trades topic, show how each one parses the message, and prove with a test run that an unknown extra field cannot break any of them.
```
Shows: cross-service reasoning. Expected answer: trade-store, risk-service and reporting-service use
Pydantic models that ignore extra fields, and market-data-service reads only `symbol` and `price`.

**4. Prove an inferred claim with a test** (local edits, ~4 min, the strongest segment)
```
/sdet-agent the MiFID demo README says DEMO_BUYER2's EURUSD order should start being rejected from about the 6th demo run because of RISK_NET_POSITION_LIMIT=5000. That was inferred, never tested. Write a risk-service unit test that sends the same 1000-lot EURUSD buy for one client six times and shows exactly which order gets rejected and why. Run it.
```
Shows: turning documentation guesswork into a verified, named regression test.

**5. How strong are the tests?** (local edits that get reverted, ~3 min)
```
/sdet-agent in reporting-service's enricher, temporarily change the deadline check from `>` to `>=`, run the unit tests and BDD suite, and tell me which test catches it. Then revert the change and confirm git diff is empty for that file.
```
Shows: a hand-made mutation test. The boundary test at exactly 60.0s should fail.

**6. Pay down known test debt** (local edits, ~5 min)
```
/sdet-agent bring fixflux/clients/fix-replay's tests in line with this repo's conventions: patch the shared Kafka factory classes instead of fix_replay.cli functions, use _make_x(**overrides) builders like risk-service's test_checker.py, and add a behave feature (Scenario Outline, at least 2 Examples rows) for the parser and report comparison. Keep coverage at or above 85%.
```
Shows: the persona enforcing its own non-negotiables on code that was written without it.

**7. BDD convention audit** (read-only, ~2 min)
```
/sdet-agent audit every .feature file in fixflux. List any plain Scenario that hard-codes values instead of using a Scenario Outline with at least 2 Examples rows, and any feature with no step definitions behind it.
```

### `/sre-agent`: the live droplet (read-only first, state changes last)

**1. Morning health check** (read-only, ~2 min, a good opener)
```
/sre-agent give me a health check of the droplet: every container's status and restart count, memory per container against the 4GB host, disk usage, and anything that restarted in the last 24h. Raw numbers first, interpretation second.
```

**2. Did the last deploy actually land?** (read-only, ~3 min)
```
/sre-agent verify the reporting-service deploy on the droplet: container up, Prometheus target healthy, regulatory_reports table exists with its uq_regulatory_reports_trade_id constraint, and a recent regulatory_report log line. Show the evidence for each.
```
Shows: "deployed" proved with evidence, not assumed. A follow-up for the same segment is
`/validate_runbook 2`, which checks the runbook commands themselves.

**3. Are the alerts really loaded?** (read-only, ~2 min)
```
/sre-agent check that Prometheus on the droplet has loaded all five rules in prometheus_alerts.yml, that MatchingEngineDown and KafkaConsumerLagHigh carry runbook_url annotations, and what is currently firing in Alertmanager. Remind me what still doesn't page anyone.
```
Expected: the honest answer that Alertmanager has no notification receivers.

**4. Kafka lag across every consumer group** (read-only, ~2 min)
```
/sre-agent show consumer lag for every consumer group on the droplet, including reporting-service, using rpk and the kafka-exporter metric. Then explain why adding a second reporting-service container would not reduce lag.
```
Expected: the single-partition ceiling.

**5. Follow one order end to end** (changes state: injects one order pair, ~5 min, the best visual)
```
/sre-agent I'm going to inject data/mifid_reporting_demo.txt through the FIX Msg Injector now. Follow the AAPL order pair through the whole system: order-service and risk-service log lines, the Tempo trace, the trade in trade-store, and the regulatory_reports row with its latency against the one-minute limit.
```
Do the injection on camera when it asks. See `fixflux/scripts/demo-mifid-reporting.md`.

**6. One-minute rule compliance** (read-only, ~2 min)
```
/sre-agent using regulatory_report_latency_seconds and the regulatory_reports table, tell me how many reports breached the one-minute RTS 1 deadline, the P99 latency, and whether the breaches correlate with consumer lag. Query Prometheus and Postgres directly.
```

**7. Capacity check before adding anything** (read-only, ~2 min)
```
/sre-agent I want to add one more Python consumer service to the droplet. Using docker stats and the compose memory limits, tell me whether it fits on the 2 vCPU / 4GB host, which containers have no memory limit, and what you'd watch after deploying.
```

**8. Game day: consumer outage without data loss** (changes state, ~6 min, the finale)
```
/sre-agent game day: stop reporting-service, inject data/mifid_reporting_demo.txt through the injector, show reporting-service consumer lag growing, start it again, show the lag drain to zero and confirm every trade produced exactly one regulatory_reports row. Follow OPERATIONS.md section 2 and ask before each state-changing step.
```
Shows: the runbook, consumer group offsets and the `trade_id` constraint working together. Nothing
is lost and nothing is duplicated.

**9. Close the alerting gap** (local edits, nothing deployed, ~4 min)
```
/sre-agent draft a MiFIDRealTimeReportingBreach rule in prometheus_alerts.yml on regulatory_report_latency_seconds (reports slower than 60s), with a runbook_url pointing at OPERATIONS.md section 4, and update that section so it's operable. Validate the PromQL, then run /predeploy-check. Don't push.
```

### Suggested running order (~25 min of footage)

| # | Segment | Why here |
|---|---|---|
| 1 | SDET 1 (health check) | Establishes that everything is green |
| 2 | SDET 4 (prove the inferred limit) | Agent writes and runs a real test |
| 3 | SDET 5 (mutation) | Shows the tests have teeth |
| 4 | SRE 1 (droplet health) | Switch to production |
| 5 | SRE 5 (follow one order) | The visual centrepiece |
| 6 | SRE 8 (game day) | Finale: failure, recovery, no data loss |

**Before recording:**
- Run `scripts/cleanup.sh` on the droplet so order books are empty.
- If the MiFID demo has been run 5 or more times since risk-service last started, restart it
  (see SDET 4).
- Keep SRE 8 last. Stopping a consumer is the only step that degrades the live stack, even briefly.
