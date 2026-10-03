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
