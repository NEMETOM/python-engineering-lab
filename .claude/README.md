# How Claude uses this directory

This file describes how Claude Code actually picks up and follows each item in `.claude/`, based
on what was observed in a VS Code extension session (October 2026). It is not official
documentation. Re-check it if the Claude Code version changes.

## The short version

Nothing in this directory is *enforced*. Each file is text that ends up in Claude's context, and
Claude follows it the way it follows any instruction: as long as it has been loaded and noticed.
What differs between files is **how** they get loaded:

| Item | How it reaches Claude | Loaded automatically? |
|---|---|---|
| `../CLAUDE.md` | Injected at the start of every session | Yes, always |
| `rules/fixflux.md` | Injected when Claude reads or edits a file matching its `paths:` (`fixflux/**`) | Yes, when it matches |
| `instructions/*.md` | Claude has to open them itself, because `CLAUDE.md` and `rules/fixflux.md` say to | No |
| `skills/*/SKILL.md` | Name and `description` are listed every session. The body loads only when the skill is invoked | Description only |
| `commands/*.md` | Listed like skills. The body loads only when you type `/<name>` | Description only |
| `agents/*.md` | Not registered as Agent-tool types here. Used only when a skill or prompt says to read one | No |
| `settings.local.json` | Read by the Claude Code harness, not by Claude | N/A (harness) |

Separately, Claude's personal memory (`~/.claude/projects/.../memory/MEMORY.md`) is also injected
every session. It holds user preferences, such as "never `git push`" and "BDD uses `Scenario
Outline`". It lives outside this repo.

## Item by item

### `CLAUDE.md` (repo root)
Always in context. It sets the monorepo map and says: before changing anything in `fixflux/`, read
`instructions/system_architecture.md` and `instructions/coding_standards.md`. It also says to treat
any mismatch between a pasted spec and those files as something to flag, not to follow blindly.

### `rules/fixflux.md`
Path-scoped: it appears automatically once Claude touches a `fixflux/**` file. It repeats the
"read the instructions first" step and adds three things:
- pasted specs that assume Hexagonal Architecture, DDD, `aiokafka` or testcontainers are describing
  a different codebase, so flag the mismatch before implementing;
- keep proposals proportionate to one 2 vCPU / 4 GB droplet;
- run `predeploy-check` before pushing `docker-compose.yml` or monitoring changes.

### `instructions/`
The ground truth Claude checks a request against:
- `system_architecture.md`: the real topic flow, services, HTTP surfaces and infrastructure. For
  example, it is why a request for a `mifid-reporting-service` runbook was flagged instead of
  written, since that service doesn't exist.
- `coding_standards.md`: synchronous `kafka-python` through the shared factory, the Pydantic vs
  dataclass split, type hints, the logging shape, the Kafka mock target in tests, the 85% coverage
  gate and the lint config.

These load **only if Claude opens them**. The rule and `CLAUDE.md` make that very likely, but if
they get skipped, the standards are simply not in context.

### `skills/`
- `sdet-agent`, `sre-agent`, `legal-counsel-agent`: thin wrappers that say "read
  `agents/<name>.md` and adopt that persona". They run in the current conversation with full tool
  access, so the `tools:` list in the agent file is guidance, not a restriction.
- `predeploy-check`: checks that every file the deploy config points at is tracked in git.

Claude invokes a skill when you type `/<skill-name>`, or when it judges that the request matches the
skill's `description`. That second path depends on Claude's judgment and can be missed.

### `commands/`
User-triggered prompt templates (`/lint`, `/test-component <path>`, `/validate_runbook`, ...).
Claude doesn't run these unprompted. `$ARGUMENTS` is replaced with whatever you type after the
command name.

### `agents/`
Persona files (SDET, SRE, legal counsel). See `agents/README.md` for how to invoke them. In this
environment they reach Claude only through the skill wrappers or a prompt such as "act as
`.claude/agents/sre_agent.md`".

### `settings.local.json`
Permission allow-list for the harness (which shell commands run without prompting). This is the
only file here that is enforced mechanically, and it governs permissions, not code style.

## What following the rules looked like in practice

**Worked well**
- `instructions/` were read before writing code. As a result, the OPERATIONS.md request was
  checked against the real stack: a non-existent service, alert and APA gateway were flagged rather
  than invented, and `kubectl` was replaced by `docker compose`/`rpk`.
- `coding_standards.md` shaped the FIX replay tool: the shared Kafka factory was extended instead
  of constructing a raw consumer, Pydantic v2 was used at the Kafka boundary and dataclasses
  in-process, log lines are decision-shaped, and the 85% CI gate and lint chain were met.

**Missed** (FIX replay task, October 2026)
- The tests patched the tool's own factory functions, not the repo-wide
  `shared.infrastructure.kafka_client.KafkaProducer`/`KafkaConsumer` target.
- The SDET persona wasn't consulted, so its `_make_x(**overrides)` builder convention wasn't
  followed.
- No `behave` feature was added, although cross-service behaviour is supposed to be tested that way.
- `predeploy-check` was recommended but not run after `docker-compose.yml` changed.

The common cause: the instruction files were read, but the persona and skill files were not,
because nothing loaded them automatically and Claude didn't invoke them on its own.

## Making the rules stick

- **Name the persona or skill in the request** (`/sdet-agent ...`, `/predeploy-check`) when it
  matters. Auto-invocation relies on Claude's judgment.
- **Put must-follow points in a path-scoped `rules/` file.** Those load without anyone remembering
  to open them. For example, a `rules/fixflux-tests.md` scoped to `fixflux/**/tests/**` could carry
  the Kafka mock target and the BDD requirement.
- **Use hooks for anything that must never be skipped**, such as running the lint chain or
  `predeploy-check` before a commit. Hooks are executed by the harness, not by Claude.
- **Keep `instructions/` accurate.** Claude treats them as ground truth. One known stale point:
  `system_architecture.md` says risk-service consumes `raw_orders`, but it consumes
  `validated_orders` (`services/risk-service/src/risk_service/config.py`, `INPUT_TOPIC`).
