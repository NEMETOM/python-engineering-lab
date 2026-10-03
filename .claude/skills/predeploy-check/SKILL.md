---
name: predeploy-check
description: Verify every file a deploy-time config (docker-compose.yml, prometheus.yml, alertmanager.yml, k8s manifests, Helm templates) points to actually exists tracked in git, not just on local disk, before assuming a push to main will deploy cleanly. Use before pushing/merging fixflux changes that touch docker-compose.yml or infrastructure/monitoring/, or when asked "is this ready to deploy" / "will the deploy work".
---

Real incident this skill exists to prevent (2026-09): `docker-compose.yml` was committed with a bind
mount pointing at a new file (`infrastructure/monitoring/prometheus_alerts.yml`), but the file
itself was never `git add`ed. On deploy, Docker's bind mount silently created the missing path as
an **empty directory** on the droplet instead of failing loudly. Prometheus then tried to read a
directory as its config file and crashed (`read ...: is a directory`), and the GitHub Actions health
check failed 22 hours later - by which point the stray directory also had to be manually removed
from the droplet before a fix could even land. See `checklist.md` for the exact verification steps.

## Before saying a deploy is ready

1. Diff what's staged/about to be pushed against what's actually committed:
   ```bash
   git status --short
   git diff --cached --stat
   ```
   A file you edited that doesn't show as staged or already committed will not reach the droplet.

2. For every config file that changed, extract every path it references and confirm each one is
   tracked in git (not just present on local disk - untracked files look identical to tracked ones
   in a normal file listing):
   ```bash
   git ls-files --error-unmatch <path>   # exits non-zero if <path> isn't tracked
   ```
   Do this for: bind mount sources in `docker-compose.yml`, `rule_files:`/scrape targets in
   `prometheus.yml`, anything `alertmanager.yml` or a Helm/K8s manifest points at.

3. If anything is untracked, stage and commit it before telling the user the deploy is ready - don't
   just flag it and move on, since an untracked config file is a silent failure mode (no error until
   the container actually starts and tries to read it).

4. See `checklist.md` for the full list of files this project's deploy pipeline actually reads, so
   you're checking real paths, not guessing at what might matter.
