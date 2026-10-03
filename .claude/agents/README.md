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
```
/sdet-agent write unit tests for the new rule
/sre-agent check why trades aren't showing up
/legal-counsel-agent review the audit trail for evidentiary defensibility
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
