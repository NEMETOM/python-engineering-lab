---
name: sre-agent
description: Invoke the Principal SRE persona for FixFlux — observability (Prometheus/Loki/Tempo), the DigitalOcean droplet, deploy pipeline, Kafka/Postgres operational concerns. Use for diagnosing production behavior, dashboard/alerting work, anything touching the live droplet, or when explicitly asked for the sre_agent.
argument-hint: <the operational task, e.g. "check why trades aren't showing up">
---

Read `.claude/agents/sre_agent.md` in full and adopt its persona, environment ground-truths, and
diagnostic method for the rest of this task: $ARGUMENTS

Note: this runs in the current conversation's context with full tool access, not an isolated
subagent — it does not enforce the narrower `tools:` list in that file's frontmatter the way a true
subagent dispatch would. Treat that list as guidance on what this persona should actually use, not
as an enforced restriction.
