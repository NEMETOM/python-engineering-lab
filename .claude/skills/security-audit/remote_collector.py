"""Read-only security data collector, run ON the droplet by audit.py.

    ssh root@<droplet> python3 - <days> <repo_dir> < remote_collector.py

Prints one JSON document to stdout. Writes nothing. Never prints a secret:
.env is read for variable names only, and Grafana's database is opened
read-only. Python 3.10 compatible (the droplet runs Ubuntu 22.04), stdlib only.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 7
REPO = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/python-engineering-lab")
FIXFLUX = os.path.join(REPO, "fixflux")
SINCE = datetime.now(timezone.utc) - timedelta(days=DAYS)
NOLOGIN = ("nologin", "false", "sync", "halt", "shutdown")


def sh(cmd: str, timeout: int = 60) -> str:
    try:
        return subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        ).stdout
    except subprocess.TimeoutExpired:
        return ""


def section(fn):
    """Run one collector; a failure becomes an error entry, not a crash."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - report, never abort the audit
        return {"error": f"{type(exc).__name__}: {exc}"}


def listeners() -> list[dict]:
    out = []
    for line in sh("ss -tlnpH").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        host, _, port = parts[3].rpartition(":")
        host = host.strip("[]").split("%")[0]
        proc = re.search(r'\(\("([^"]+)"', line)
        out.append({"host": host, "port": port, "process": proc.group(1) if proc else ""})
    return out


def containers() -> list[dict]:
    fmt = "\t".join(("{{.Names}}", "{{.Image}}", '{{.Label "com.docker.compose.project"}}',
                     '{{.Label "com.docker.compose.service"}}', "{{.Status}}"))
    rows = []
    for line in sh(f"docker ps -a --format '{fmt}'").splitlines():
        name, image, project, service, status = (line.split("\t") + [""] * 5)[:5]
        rows.append({"name": name, "image": image, "project": project, "service": service, "status": status})
    return rows


def grafana_container() -> str:
    return sh("docker ps -q --filter label=com.docker.compose.service=grafana").strip()


def grafana_db() -> dict:
    cid = grafana_container()
    if not cid:
        return {"error": "grafana container not running"}
    mounts = json.loads(sh(f"docker inspect -f '{{{{json .Mounts}}}}' {cid}") or "[]")
    src = next((m["Source"] for m in mounts if m.get("Destination") == "/var/lib/grafana"), None)
    if not src:
        return {"error": "grafana data mount not found"}
    db = sqlite3.connect(f"file:{src}/grafana.db?mode=ro", uri=True)

    def rows(sql: str) -> list:
        try:
            return [list(r) for r in db.execute(sql).fetchall()]
        except sqlite3.Error as exc:
            return [["error", str(exc)]]

    plugins_dir = os.path.join(src, "plugins")
    return {
        "users": rows(
            "SELECT id, login, is_admin, is_disabled, created, last_seen_at, "
            "COALESCE(is_service_account, 0) FROM user ORDER BY id"
        ),
        "tokens": rows(
            "SELECT user_id, client_ip, substr(user_agent, 1, 60), created_at "
            "FROM user_auth_token ORDER BY created_at"
        ),
        "api_keys": rows("SELECT name, role, created FROM api_key"),
        "datasources": rows("SELECT name, type, url, user FROM data_source ORDER BY name"),
        "plugins": sorted(os.listdir(plugins_dir)) if os.path.isdir(plugins_dir) else [],
    }


def grafana_default_login() -> str:
    # The exact probe that would have caught the 2026-11-16 incident.
    return sh(
        "curl -s -o /dev/null -m 5 -w '%{http_code}' -u admin:admin "
        "http://127.0.0.1:3000/api/user"
    ).strip()


def grafana_log() -> dict:
    # Grafana logs only requests that did NOT return 200/304, so successful
    # API calls (e.g. creating a user) never appear here. Failed logins and
    # authenticated non-200 requests still do.
    cid = grafana_container()
    if not cid:
        return {"error": "grafana container not running"}
    text = sh(f"docker logs --since {DAYS * 24}h {cid} 2>&1", timeout=120)
    started = sh(f"docker inspect -f '{{{{.State.StartedAt}}}}' {cid}").strip()
    failed: dict[str, int] = {}
    authed: dict[str, int] = {}
    by_ip: dict[str, int] = {}
    for line in text.splitlines():
        ip = re.search(r"remote_addr=(\S+)", line)
        if not ip or "Request Completed" not in line:
            continue
        ip = ip.group(1)
        by_ip[ip] = by_ip.get(ip, 0) + 1
        if "path=/login" in line and "status=401" in line:
            failed[ip] = failed.get(ip, 0) + 1
        uname = re.search(r"uname=(\S+)", line)
        if uname:
            key = f"{uname.group(1)}@{ip}"
            authed[key] = authed.get(key, 0) + 1
    return {"container_started": started, "failed_logins": failed,
            "authenticated_requests": authed, "requests_by_ip": by_ip}


def ssh_activity() -> dict:
    since = SINCE.strftime("%Y-%m-%d %H:%M:%S")
    text = sh(f"journalctl _COMM=sshd --since '{since}' --no-pager -o short-iso", timeout=120)
    accepted = []
    failed: dict[str, int] = {}
    for line in text.splitlines():
        m = re.search(r"^(\S+).*Accepted (\S+) for (\S+) from (\S+) port \d+ ssh2(?:: \S+ (\S+))?", line)
        if m:
            accepted.append({"time": m.group(1), "method": m.group(2), "user": m.group(3),
                             "ip": m.group(4), "fingerprint": m.group(5) or ""})
            continue
        m = re.search(r"(?:Failed \S+ for (?:invalid user )?\S+|Invalid user \S+) from (\S+)", line)
        if m:
            failed[m.group(1)] = failed.get(m.group(1), 0) + 1
    config = {}
    for line in sh("sshd -T 2>/dev/null").splitlines():
        key, _, value = line.partition(" ")
        if key in ("passwordauthentication", "permitrootlogin", "pubkeyauthentication",
                   "kbdinteractiveauthentication"):
            config[key] = value
    return {"accepted": accepted, "failed_by_ip": failed, "sshd": config}


def authorized_keys() -> list[dict]:
    homes = ["/root"] + [os.path.join("/home", h) for h in sorted(os.listdir("/home"))]
    out = []
    for home in homes:
        path = os.path.join(home, ".ssh", "authorized_keys")
        if not os.path.isfile(path):
            continue
        mtime = datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).isoformat()
        for line in sh(f"ssh-keygen -lf {path}").splitlines():
            parts = line.split()
            out.append({"file": path, "mtime": mtime, "fingerprint": parts[1] if len(parts) > 1 else "",
                        "comment": " ".join(parts[2:])})
    return out


def accounts() -> dict:
    login, uid0 = [], []
    for line in open("/etc/passwd"):
        f = line.strip().split(":")
        if len(f) < 7:
            continue
        if f[2] == "0":
            uid0.append(f[0])
        if not f[6].endswith(NOLOGIN):
            login.append(f[0])
    crons = {}
    for user in [line.split(":")[0] for line in open("/etc/passwd")]:
        entries = [e for e in sh(f"crontab -l -u {user} 2>/dev/null").splitlines()
                   if e.strip() and not e.lstrip().startswith("#")]
        if entries:
            crons[user] = entries
    return {"login_capable": login, "uid0": uid0, "crontabs": crons}


def recent_changes() -> dict:
    since = SINCE.strftime("%Y-%m-%d %H:%M:%S")
    files = sh(
        f"find /etc /root /usr/local /opt /var/spool/cron -xdev -type f -newermt '{since}' 2>/dev/null",
        timeout=120,
    ).split()
    units = sh(
        f"find /etc/systemd/system /lib/systemd/system -xdev -type f -newermt '{since}' 2>/dev/null"
    ).split()
    return {"files": files, "systemd_units": units}


def env_file() -> dict:
    path = os.path.join(FIXFLUX, ".env")
    if not os.path.isfile(path):
        return {"present": False}
    names = [row.split("=", 1)[0].strip() for row in open(path)
             if "=" in row and not row.lstrip().startswith("#")]
    st = os.stat(path)
    return {"present": True, "names": names, "mode": oct(st.st_mode & 0o777),
            "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()}


print(json.dumps({
    "collected_at": datetime.now(timezone.utc).isoformat(),
    "days": DAYS,
    "hostname": sh("hostname").strip(),
    "listeners": section(listeners),
    "containers": section(containers),
    "grafana_db": section(grafana_db),
    "grafana_default_login": section(grafana_default_login),
    "grafana_log": section(grafana_log),
    "ssh": section(ssh_activity),
    "authorized_keys": section(authorized_keys),
    "accounts": section(accounts),
    "recent_changes": section(recent_changes),
    "env_file": section(env_file),
}))
