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

### `/sdet-agent`: Playwright UI tests (fixflux/tests/ui, no droplet)

The Console UI suite runs hermetically: a real compliance-api plus a real Chromium, with Kafka,
Postgres and the market data WebSocket faked. That makes it safe to record anywhere. One-time setup
is in `fixflux/tests/ui/README.md` (`pip install -r requirements.txt`,
`python -m playwright install chromium`).

**8. Run the UI scenarios and report per tab** (read-only, ~2 min)
```
/sdet-agent run the Playwright UI suite in fixflux/tests/ui with python -m behave. Give me one table: feature (Console tab), scenarios passed/failed, and what each scenario proves. If anything fails, open the Playwright trace in tests/ui/artifacts and tell me which step failed and why.
```
Shows: real browser tests for all three tabs in about 2 seconds, explained in plain terms.

**9. Watch the browser** (read-only, ~2 min, the best visual for this segment)
```
/sdet-agent run the Market Data and Fix Msg Injector UI features headed and slowed down (UI_HEADED=1, UI_SLOW_MO=500) so I can record the browser, then summarise what each scenario did on screen.
```
Shows: Chromium visibly typing FIX orders, toggling, and Market Data rows appearing as snapshots
are pushed through the mocked WebSocket. Set up screen capture before sending the prompt.

**10. Add a scenario the page-object way** (local edits, ~5 min)
```
/sdet-agent add a happy-path UI scenario for the Market Data tab: a one-sided book (bid only, then ask only) shows "-" for the missing side, mid and spread. Use a Scenario Outline with at least 2 Examples rows, put any new locator in tests/ui/pages, keep assertions in the steps, run the suite, then break the page on purpose to prove the new scenario catches it, and restore it.
```
Shows: the persona following the suite's conventions (page objects own locators, BDD outlines,
mutation check) instead of just writing a test that passes.

**11. Run the UI tests on GitHub Actions** (changes state: starts a CI run, ~4 min)
```
/sdet-agent start the Console UI Tests workflow on the fix-flux branch with the GitHub CLI, watch it to completion, and report the result. If a scenario fails, download the playwright-traces artifact and explain the failure.
```
Needs the GitHub CLI installed and logged in (see `fixflux/tests/ui/GITHUB_CLI_SETUP.md`). Without
it, the agent should say so and point you to the Actions tab.

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

---

## Demo playbook: `/legal-counsel-agent`

This persona's value is in what it *refuses* to overstate, so the best segments are ones where it
separates (a) what it read in the code, (b) the real regulatory concept it maps to, and
(c) controls that don't exist yet. Several prompts are built around real gaps it should find.

The same labels as above apply. Additionally, **never run a tamper experiment against the
droplet's database.** Altering or deleting `compliance_audit_trail` rows destroys the very evidence
the demo is about. Those prompts say "local stack" explicitly.

**1. What does the audit trail actually prove?** (read-only, ~2 min, a good opener)
```
/legal-counsel-agent a regulator asks whether FixFlux's compliance audit trail is tamper-proof. Read the AuditLogger and the compliance_audit_trail model and answer: what exactly does the SHA-256 checksum prove, what does it not prove, and how would you word it in a filing without overstating it?
```
Expected: "per-record tamper-evidence, not chain-of-custody". There's no hash chain, so a deleted
row is undetectable.

**2. Prove it: build a verifier, then tamper** (local edits + local DB only, ~6 min, the strongest segment)
```
/legal-counsel-agent no hash verifier exists in this codebase. Write a small script that recomputes the SHA-256 of every compliance_audit_trail row using the same canonicalization as AuditLogger and reports mismatches. Then, on my LOCAL docker stack only, show three cases: an untouched table verifies clean, a row with an edited payload is flagged, and a deleted row is NOT detected. Ask before modifying any row.
```
Shows: the guarantee and its limit demonstrated live, not just asserted.

**3. Close the gap: design a hash chain** (local edits, ~4 min)
```
/legal-counsel-agent propose the smallest change that turns per-record tamper-evidence into a hash chain for compliance_audit_trail: the prev_checksum design, how existing rows are migrated, and what the chain still would NOT prove (e.g. truncation of the newest rows, a rewritten chain). Write it as a design note, don't implement it.
```

**4. Who can switch surveillance off?** (read-only, ~3 min, a finding that lands well)
```
/legal-counsel-agent the compliance admin panel can toggle rules like WashTradingRule live. If an operator disabled it for an hour and re-enabled it, what evidence would remain - in compliance_rule_overrides, the audit trail and the logs? What would a regulator expect to see instead?
```
Expected: one row per rule, overwritten in place (`rule_id` primary key, `updated_at` overwritten),
no "who", no history, and not written to the audit trail. Only a log line records the toggle.

**5. Map a rule to its legal basis** (read-only, ~3 min)
```
/legal-counsel-agent map WashTradingRule and RapidFireRule to the market abuse concepts they illustrate. Use the real trigger conditions from the rule files and the thresholds in compliance_policies.yaml (300s wash-trading window, 10 orders per 60s), and be explicit about where the mapping is illustrative rather than a compliance claim.
```

**6. Investigation pack for one client** (read-only on the droplet, ~5 min)
```
/legal-counsel-agent a regulator requests everything FixFlux holds about client DEMO_BUYER1 for today. Check what Kafka still retains on the live broker (rpk), then assemble the evidence from the durable Postgres sources instead: orders in the audit trail, violations, trades, regulatory_reports. Say which source each item came from and what can no longer be reconstructed.
```
Shows: the persona's "prefer SQL over Kafka replay" rule applied to a concrete request.

**7. Review the MiFID II reporting service** (read-only, ~4 min)
```
/legal-counsel-agent review services/reporting-service as a regulator would. Is the separation between the public RTS 1 fields and the restricted RTS 22 fields real in the schema? What are the evidentiary risks: synthetic LEIs, INCOMPLETE reports, the trade_id uniqueness guarantee, and a matching-engine replay that regenerates trade IDs?
```
Expected to surface: the `trade_id` constraint can't catch a replay that issues new trade IDs, and
no APA publication exists.

**8. Test data in the evidence record** (read-only, ~3 min)
```
/legal-counsel-agent fix-replay publishes replayed orders to raw_orders with client IDs like RPL-<run>-<client>. Does compliance-consumer write those into compliance_audit_trail and compliance_violations alongside real activity? What does that mean for the integrity of the record, and how should replayed activity be segregated?
```

**9. Timestamps and clock sync** (read-only, ~3 min)
```
/legal-counsel-agent explain MiFID II RTS 25 clock-synchronisation requirements conceptually, then list every place FixFlux stamps time (services calling datetime.now, Postgres defaults, Kafka timestamps) and what would be needed before any of these timestamps could be relied on as evidence. Don't claim the system complies.
```

**10. Controls inventory memo** (local edits: writes one markdown file, ~4 min, the closer)
```
/legal-counsel-agent write a one-page controls inventory memo for a compliance officer: each control FixFlux has (pre-trade risk checks, surveillance rules, audit checksums, regulatory reporting), its evidence source, and its main limitation. Tag every statement as (a) verified in code, (b) regulatory concept, or (c) missing control. Save it as fixflux/docs/controls-inventory.md.
```

### Suggested running order (~20 min of footage)

| # | Segment | Why here |
|---|---|---|
| 1 | Legal 1 (what the checksum proves) | Sets up the core distinction |
| 2 | Legal 2 (verifier + tamper) | Proves it live: edit caught, deletion missed |
| 3 | Legal 4 (who can switch surveillance off) | A governance gap people don't expect |
| 4 | Legal 7 (reporting-service review) | Ties to the MiFID II feature |
| 5 | Legal 10 (controls memo) | Closes with a deliverable |

**Before recording:**
- Segment 2 needs the stack running **locally**, with some orders injected so the audit trail
  has rows.
- Segment 6 queries the droplet and may show client IDs and order data on screen. Use demo clients
  only.
- These answers draw on regulatory concepts. The persona labels them as illustrative, and the video
  shouldn't present them as legal advice.

---

## Demo playbook: security audit with `/sre-agent`

A read-only security audit of FixFlux in three passes: the repo, the droplet as an outsider sees
it, and the droplet from inside. It produces a findings table with evidence and a suggested fix for
each item. Fixes are a separate, optional segment, so the audit itself never changes anything.

**Ground rules (say them on camera; they're part of the demo):**
- **Only your own droplet.** Port checks and requests go to your droplet's IP, nowhere else.
- **Observe, don't exploit.** The agent shows that a port is open or an endpoint answers. It does
  not publish to Kafka, toggle rules, call Prometheus's `/-/quit`, or log in with found credentials.
- **Evidence or it didn't happen.** Every finding needs a command output, file and line, or config
  value, and is labelled *verified* or *inferred*.

### Segment A: the full audit (read-only, ~10 min)

```
/sre-agent run a read-only security audit of FixFlux. Three passes:
1. Repo: committed secrets and default credentials, published ports in docker-compose.yml (which are 0.0.0.0 vs 127.0.0.1), containers running as root, unpinned GitHub Actions, unauthenticated HTTP endpoints, dangerous flags like --web.enable-lifecycle.
2. Outside view: from my laptop, check which of the droplet's ports are actually reachable. Only my droplet's IP, connection checks only.
3. Inside view: on the droplet, check ufw/firewall state, SSH config (root login, password auth), docker ps port bindings, and the grafana_reader role's limits.
Don't exploit anything and don't change anything. Output one table: severity, finding, evidence (verified/inferred), impact, suggested fix, effort. Then the top 3 to fix first and why.
```

### Expected findings (check the agent's output against this list)

Verified in the repo when this playbook was written. Some may already be fixed by the time you
record, and finding that out is a good result in itself.

| Area | Expected finding | Why it matters | Likely fix |
|---|---|---|---|
| Kafka | Redpanda published on `9092` on all interfaces, no auth | Anyone can publish fake orders or trades, which flow into `trades` and `regulatory_reports` | Bind to `127.0.0.1`; host clients already use localhost |
| HTTP | compliance-api `8010`: FIX injector and rule-toggle admin panel with no authentication | Anyone can inject orders or switch surveillance rules off | Loopback plus SSH tunnel, or basic auth in front |
| Monitoring | Prometheus `9090` public with `--web.enable-lifecycle` | Anyone can reload or shut down Prometheus | Drop the flag or bind to `127.0.0.1` |
| Monitoring | Alertmanager `9093`, Loki `3100`, Tempo `3200`/`4318` public | Silence alerts, read logs, push fake traces | Bind to `127.0.0.1`; Grafana reaches them over the compose network |
| Grafana | Public on `3000`; password strength depends on `.env` | Admin access means Explore across all datasources | Strong password (done via `.env`); optionally firewall to your IP |
| Secrets | `fixuser`/`fixpass` in `docker-compose.yml`, `k8s/02-secret.yaml` and docs | Anyone reading the repo has DB credentials | Move to `.env`; rotate. Postgres is already loopback-only, which limits the damage |
| Containers | 0 of 10 FixFlux Dockerfiles set a non-root `USER` | A compromised service runs as root in its container | Add `USER` to each Dockerfile |
| Host | Deploys SSH in as `root` | A leaked deploy key is full root on the droplet | Dedicated deploy user in the `docker` group |
| CI | 3 GitHub Action references pinned to mutable tags (`dorny/test-reporter@v1` twice, `peaceiris/actions-gh-pages@v3`); the other 39 are pinned to SHAs | A moved tag can run new code in CI | Pin to commit SHAs like the rest |
| Already hardened | Postgres on `127.0.0.1:5433`; `grafana_reader` read-only with timeouts and a 3-connection limit; `.env` gitignored | Should be reported as passing checks | (none) |

A good audit also says what it **couldn't** check, e.g. the DigitalOcean cloud firewall, which
lives in DigitalOcean's control panel rather than on the droplet.

### Segment B: fix the top finding (local edits, ~5 min)

```
/sre-agent fix the highest-severity finding from the audit in the repo only: make the change, explain what breaks for whom (CI, host scripts, my browser access), run /predeploy-check, and give me the exact post-deploy verification command. Don't push.
```

The likely pick is binding Redpanda, compliance-api and the monitoring ports to `127.0.0.1`. That
has a real trade-off worth showing on camera: the FixFlux Console then needs an SSH tunnel.

### Segment C: re-audit to prove the fix (read-only, ~3 min)

After deploying Segment B:
```
/sre-agent re-run only the outside-view pass of the security audit and compare with the previous findings table: which findings are now closed, with evidence?
```

**Before recording:**
- **Blur the droplet IP**, and any password that might show in `.env` or command output.
- **Start the audit from your laptop**, not from an SSH session on the droplet. Otherwise the
  outside-view pass tests the droplet from itself, where every port looks reachable.
- **Keep Segment B separate.** If the audit and the fix are in one take, it's harder to show that
  the audit itself changed nothing.
