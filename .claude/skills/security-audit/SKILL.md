---
name: security-audit
description: Read-only security audit of the FixFlux droplet - public exposure, default credentials, unexpected Grafana admins and sessions, SSH login sources and keys, persistence (cron, systemd, accounts, changed files), secrets in .env. Use when asked for a security audit/check, "anything suspicious?", after an incident, before a demo or recording, or periodically. Run as the SRE persona.
argument-hint: "[--days N] [focus, e.g. 'grafana' or 'ssh']"
---

Act as the SRE persona: read `.claude/agents/sre_agent.md` first if you haven't this session.
Arguments: $ARGUMENTS

Built from the 2026-11-16 Grafana incident (see `.claude/rules/fixflux.md`). The compose file fell
back to `admin/admin` on a public port. An outside IP logged in, created a server admin
(`hxops_89cnx7`) and deleted `admin`. Nothing alerted. The owner only noticed because they
couldn't log in. Every check below either would have caught it, or covers the next most likely
way in.

## Run it

```bash
python .claude/skills/security-audit/audit.py --host <droplet-ip> --days 7
```

- Take the droplet IP from your memory notes or ask the user. **Never write it into a repo
  file**: the workflows keep it in a secret (`DO_DROPLET_IP`).
- Exit code: `2` = at least one ALERT, `1` = WARN, `0` = clean.
- `--json-out <scratchpad path>` keeps the raw data, for digging into a finding. It holds IPs
  and account names, so write it to the scratchpad, never into the repo.
- `--no-external` skips the port probe and IP lookups (offline).

What it does, all read-only:

| Area | Checks | Would have caught 11-16? |
|---|---|---|
| compose (static) | credential vars with a `:-default`, hard-coded passwords | yes: `:-admin` |
| exposure | sensitive ports (Grafana, Postgres) bound publicly or reachable from outside; unexpected listeners; the accepted-but-unauthenticated public ports | yes: 3000 public |
| grafana | `admin/admin` probe, admins not in the baseline, new accounts, sessions from public IPs, API keys, data sources not in provisioning, authenticated requests from public IPs in the log | yes, 4 ways |
| ssh | logins with keys not in the baseline, login sources classified as this machine / GitHub Actions / unclassified, sshd auth settings | - |
| host | extra uid-0 or login accounts, crontabs, unknown authorized keys, changed security files and systemd units, containers outside the compose project | - |
| secrets | required `.env` names present (values never read), file mode 600 | yes: password missing |

## How to report

Lead with the ALERT count, then each ALERT and WARN in one line with what to do. Keep the
distinction this project insists on: **verified** (a log line, a DB row) versus **inferred**.

Known blind spots, to state rather than paper over:
- **Grafana doesn't log 200 responses.** A successful attacker API call (creating a user,
  deleting one) leaves no request log; only the resulting DB state shows it. Never conclude "no
  request did X" from the Grafana log.
- **Logs die with their container.** A recreate (deploy, `up -d` after a config change) wipes that
  container's log. The report states the Grafana log's start time.
- **Unclassified SSH sources aren't proof of compromise.** On 2026-11-16 the
  `3.41.x`/`3.42.x` logins with the deploy key were a recurring, unexplained source. Ask the user
  what they are and record the answer in `baseline.json`; don't guess.
- It checks this droplet only, not GitHub (secrets, Actions logs) or DigitalOcean's account.

## If there's an ALERT: incident playbook

Do these **in order**, confirm each containment step with the user, and never skip step 1.

1. **Preserve evidence first** (writes only to a new `/root/incident-<timestamp>/`):
   ```bash
   ssh -i ~/.ssh/fixflux_do root@<droplet> 'bash -s' < .claude/skills/security-audit/collect_evidence.sh
   ```
   A container recreate destroys its logs, and containment usually recreates one.
2. **Establish the path in** before acting. Who (IP, account, key), when, through what (web login,
   API, SSH). Correct earlier conclusions out loud when new data contradicts them. On 11-16 the
   first theory (SSH access) was wrong.
3. **Contain:** close the exposure, for example bind the port to `127.0.0.1` in
   `docker-compose.yml` on the droplet **and** in the repo. Then revoke the attacker's access
   (sessions, accounts, keys). Rebuilding from provisioned config on a fresh volume beats
   editing a compromised one.
4. **Fix the root cause in the repo** so a redeploy can't reintroduce it. Commit, and tell the user
   to push **before** the next deploy, then to `git checkout -- <file> && git pull` on the
   droplet, or the pull fails (it did on 11-17).
5. **Record it:** add the rule and the reason to `.claude/rules/fixflux.md`, and update
   `baseline.json` (for example a new expected admin login or key fingerprint).

Never print or paste a secret in the conversation. Generate passwords on the droplet, verify them
there (`curl -u` returning 200), and hand them over through a file the user deletes after copying.

## Keeping it accurate

- `baseline.json` is the expected state. Change it only with a reason, never just to silence a
  finding nobody has explained.
- New public port or service: add it to `accepted_public_ports` (with "NO AUTH" if it has none)
  or `sensitive_ports`.
- New deploy key: add its fingerprint (`ssh-keygen -lf <pubkey>`); retire the old one.
- `remote_collector.py` must stay Python 3.10 + stdlib (the droplet's interpreter) and read-only.
