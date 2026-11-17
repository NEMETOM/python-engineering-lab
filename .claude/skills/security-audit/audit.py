"""Basic, read-only security audit of the FixFlux droplet.

usage:
    python .claude/skills/security-audit/audit.py --host <droplet-ip> [--days 7]
        [--key ~/.ssh/fixflux_do] [--json-out raw.json] [--no-external]

Runs remote_collector.py on the droplet over SSH (read-only), probes the
droplet's ports from this machine, statically checks docker-compose.yml, and
grades everything against baseline.json. Prints a Markdown report.

Exit code: 2 if any ALERT, 1 if any WARN, 0 otherwise.
Never prints secrets. The report does contain IP addresses: don't commit it.
"""

import argparse
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIXFLUX = REPO / "fixflux"
SEVERITIES = ("ALERT", "WARN", "INFO")


class Findings:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []

    def add(self, severity: str, area: str, message: str) -> None:
        self.items.append((severity, area, message))

    def count(self, severity: str) -> int:
        return sum(1 for s, _, _ in self.items if s == severity)


def is_internal(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return False
    # 0.0.0.0 and :: mean "all interfaces", i.e. PUBLIC - but ipaddress counts
    # them as private, which once made this check skip every public listener.
    if addr.is_unspecified:
        return False
    return addr.is_loopback or addr.is_private


def fetch(url: str) -> str | None:
    """HTTPS GET with certificate verification always on. Falls back to curl:
    on Windows, Python's CA bundle can fail on chains that curl (system store)
    verifies fine - observed with api.github.com."""
    headers = {"User-Agent": "fixflux-security-audit"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode()
    except OSError:
        pass
    try:
        proc = subprocess.run(["curl", "-fsS", "--max-time", "15", "-A", headers["User-Agent"], url],
                              capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.decode() if proc.returncode == 0 else None


def github_actions_networks() -> list | None:
    body = fetch("https://api.github.com/meta")
    if body is None:
        return None
    return [ipaddress.ip_network(c) for c in json.loads(body).get("actions", [])]


def classify(ip: str, my_ip: str | None, gh_nets: list | None) -> str:
    if ip == my_ip:
        return "this machine"
    if is_internal(ip):
        return "internal"
    if gh_nets is None:
        return "unclassified (GitHub ranges unavailable)"
    addr = ipaddress.ip_address(ip)
    if any(addr in net for net in gh_nets if net.version == addr.version):
        return "GitHub Actions"
    return "unclassified"


def collect_remote(host: str, key: str, days: int) -> dict:
    proc = subprocess.run(
        ["ssh", "-i", os.path.expanduser(key), "-o", "BatchMode=yes",
         "-o", "ConnectTimeout=15", f"root@{host}",
         "python3", "-", str(days), "~/python-engineering-lab"],
        input=(HERE / "remote_collector.py").read_bytes(),
        capture_output=True, timeout=600,
    )
    if proc.returncode != 0:
        sys.exit(f"remote collector failed ({proc.returncode}): {proc.stderr.decode()[-500:]}")
    return json.loads(proc.stdout)


def probe(host: str, ports: list[str]) -> dict[str, bool]:
    result = {}
    for port in ports:
        try:
            with socket.create_connection((host, int(port)), timeout=3):
                result[port] = True
        except OSError:
            result[port] = False
    return result


# ── checks ───────────────────────────────────────────────────────────────────


def check_compose(f: Findings) -> None:
    text = (FIXFLUX / "docker-compose.yml").read_text(encoding="utf-8")
    for m in re.finditer(r"\$\{(\w*(?:PASSWORD|SECRET|TOKEN)\w*):-([^}]+)\}", text):
        f.add("ALERT", "compose", f"`{m.group(1)}` falls back to a non-empty default "
              f"(`:-{m.group(2)}`): a missing .env value silently becomes a known credential "
              "(the 2026-11-16 Grafana incident).")
    for m in re.finditer(r"(?m)^\s+(\w*(?:PASSWORD|SECRET)\w*):\s*[\"']?(?!\$\{)([^\s\"'#]+)", text):
        f.add("WARN", "compose", f"hard-coded credential `{m.group(1)}` in docker-compose.yml "
              "(only acceptable if the service is loopback-only).")


def _port_list(ports: set[str], base: dict) -> str:
    names = base["accepted_public_ports"]
    return ", ".join(f"{p} ({names.get(p, '?').split(' - ')[0]})" for p in sorted(ports, key=int))


def check_listeners(f: Findings, d: dict, base: dict, open_ports: dict[str, bool]) -> None:
    """Two layers: what the droplet binds publicly, and what the internet can
    actually reach (a DigitalOcean cloud firewall filters most ports). Without
    the external probe, every public bind is treated as reachable."""
    sensitive, accepted = base["sensitive_ports"], base["accepted_public_ports"]
    host_ok = base["host_listeners"]
    public: set[str] = set()
    for lst in d["listeners"]:
        if is_internal(lst["host"]):
            continue
        port, proc = lst["port"], lst["process"]
        public.add(port)
        if port in sensitive:
            f.add("ALERT", "exposure", f"sensitive port {port} ({sensitive[port]}) binds "
                  f"{lst['host']} - must be 127.0.0.1 only.")
        elif port not in accepted:
            f.add("WARN", "exposure", f"unexpected public listener {lst['host']}:{port} ({proc}).")
        if proc not in ("docker-proxy", "sshd") and port not in host_ok:
            f.add("WARN", "host", f"non-container process `{proc}` listens publicly on {port}.")
    unauth = {p for p in public if "NO AUTH" in accepted.get(p, "")}
    if not open_ports:
        if unauth:
            f.add("WARN", "exposure", f"bound publicly, unauthenticated: {_port_list(unauth, base)} "
                  "(reachability not probed: --no-external).")
        return
    reachable = {p for p in unauth if open_ports.get(p)}
    filtered = public - {p for p, o in open_ports.items() if o}
    if reachable:
        f.add("WARN", "exposure", "reachable from the internet with NO authentication: "
              f"{_port_list(reachable, base)}.")
    if filtered:
        f.add("INFO", "exposure", "bound on all interfaces but filtered from outside (probably a "
              "DigitalOcean cloud firewall - then that firewall is the only thing protecting "
              f"them; a rule change exposes them): {_port_list(filtered, base)}.")


def check_external(f: Findings, open_ports: dict[str, bool], base: dict) -> None:
    for port, is_open in sorted(open_ports.items(), key=lambda kv: int(kv[0])):
        if not is_open:
            continue
        if port in base["sensitive_ports"]:
            f.add("ALERT", "exposure", f"port {port} ({base['sensitive_ports'][port]}) is "
                  "reachable FROM THE INTERNET.")
        elif port not in base["accepted_public_ports"]:
            f.add("WARN", "exposure", f"port {port} is reachable from the internet and not in baseline.")


def check_grafana(f: Findings, d: dict, base: dict, days: int) -> None:
    if d["grafana_default_login"] == "200":
        f.add("ALERT", "grafana", "admin/admin LOGS IN. Rotate the password now.")
    db = d["grafana_db"]
    if "error" in db:
        f.add("WARN", "grafana", f"could not read grafana.db: {db['error']}")
        return
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    for uid, login, is_admin, _disabled, created, _last_seen, is_sa in db["users"]:
        if is_admin and login not in base["grafana_admin_logins"]:
            f.add("ALERT", "grafana", f"unexpected SERVER ADMIN `{login}` (id {uid}, created "
                  f"{created}). Preserve evidence before touching it.")
        elif str(created) >= cutoff:
            f.add("WARN", "grafana", f"account `{login}` (id {uid}) created {created}.")
        if is_sa:
            f.add("WARN", "grafana", f"service account `{login}` exists (id {uid}).")
    if not any(row[1] in base["grafana_admin_logins"] for row in db["users"]):
        f.add("ALERT", "grafana", f"expected admin account(s) {base['grafana_admin_logins']} missing.")
    for uid, ip, agent, created in db["tokens"]:
        if ip and not is_internal(ip):
            when = datetime.fromtimestamp(created, timezone.utc).isoformat() if created else "?"
            f.add("ALERT", "grafana", f"active session for user id {uid} from PUBLIC IP {ip} "
                  f"(created {when}, agent `{agent}`). Grafana is meant to be loopback-only.")
    for name, role, created in db["api_keys"]:
        f.add("WARN", "grafana", f"API key `{name}` ({role}) created {created}.")
    provisioned = set()
    for yml in (FIXFLUX / "infrastructure/monitoring/grafana/provisioning/datasources").glob("*.y*ml"):
        provisioned |= set(re.findall(r"(?m)^\s*-?\s*name:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
                                      yml.read_text(encoding="utf-8")))
    for name, typ, url, user in db["datasources"]:
        if name not in provisioned:
            f.add("WARN", "grafana", f"data source `{name}` ({typ}, {url}, user `{user}`) is not "
                  "in provisioning/datasources/ - added through the UI or API.")
    if db["plugins"]:
        f.add("INFO", "grafana", f"plugins installed: {', '.join(db['plugins'])}.")

    log = d["grafana_log"]
    if "error" in log:
        return
    for key, n in sorted(log["authenticated_requests"].items()):
        user, _, ip = key.rpartition("@")
        if not is_internal(ip):
            f.add("ALERT", "grafana", f"{n} authenticated non-200 request(s) as `{user}` from "
                  f"PUBLIC IP {ip}. (Grafana doesn't log 200s, so successful calls are invisible.)")
    public_failed = {ip: n for ip, n in log["failed_logins"].items() if not is_internal(ip)}
    if public_failed:
        f.add("WARN", "grafana", f"failed logins from public IPs: {public_failed}.")
    f.add("INFO", "grafana", f"log window starts at container start {log['container_started']} "
          "or the audit window, whichever is later: a container recreate erases older logs.")


def check_ssh(f: Findings, d: dict, base: dict, my_ip: str | None, gh_nets) -> dict:
    s = d["ssh"]
    known = base["authorized_key_fingerprints"]
    by_ip: dict[str, list] = defaultdict(list)
    for a in s["accepted"]:
        by_ip[a["ip"]].append(a)
        if a["fingerprint"] and a["fingerprint"] not in known:
            f.add("ALERT", "ssh", f"login as {a['user']} at {a['time']} from {a['ip']} with "
                  f"UNKNOWN key {a['fingerprint']}.")
    classes = {ip: classify(ip, my_ip, gh_nets) for ip in by_ip}
    unclassified = sorted(((ip, v) for ip, v in by_ip.items()
                           if classes[ip].startswith("unclassified")), key=lambda kv: -len(kv[1]))
    if unclassified:
        shown = "; ".join(f"{ip} x{len(v)} (last {v[-1]['time'][:16]})" for ip, v in unclassified[:8])
        more = f"; +{len(unclassified) - 8} more" if len(unclassified) > 8 else ""
        f.add("WARN", "ssh", f"{sum(len(v) for _, v in unclassified)} root login(s) from "
              f"{len(unclassified)} source(s) that are neither this machine nor GitHub Actions: "
              f"{shown}{more}. Confirm what runs there (CI, an agent, a teammate) - if nothing "
              "you know, treat the deploy key as compromised.")
    cfg = s["sshd"]
    if cfg.get("passwordauthentication") == "yes":
        f.add("WARN", "ssh", "PasswordAuthentication is enabled.")
    if cfg.get("permitrootlogin") == "yes":
        f.add("INFO", "ssh", "PermitRootLogin yes (passwords are off, so key-only in practice; "
              "`prohibit-password` would make that explicit).")
    total_failed = sum(s["failed_by_ip"].values())
    if total_failed:
        top = Counter(s["failed_by_ip"]).most_common(3)
        f.add("INFO", "ssh", f"{total_failed} failed SSH attempts from {len(s['failed_by_ip'])} "
              f"IPs (internet background noise unless logins also succeed); top: {top}.")
    return {ip: (classes[ip], len(v)) for ip, v in by_ip.items()}


def check_host(f: Findings, d: dict, base: dict, days: int) -> None:
    for k in d["authorized_keys"]:
        if k["fingerprint"] not in base["authorized_key_fingerprints"]:
            f.add("ALERT", "host", f"unknown key in {k['file']}: {k['fingerprint']} {k['comment']}.")
        if datetime.fromisoformat(k["mtime"]) > datetime.now(timezone.utc) - timedelta(days=days):
            f.add("WARN", "host", f"{k['file']} modified {k['mtime']}.")
    acc = d["accounts"]
    for user in acc["uid0"]:
        if user != "root":
            f.add("ALERT", "host", f"extra uid-0 account `{user}`.")
    others = [u for u in acc["login_capable"] if u != "root"]
    if others:
        f.add("WARN", "host", f"login-capable accounts besides root: {others}.")
    for user, entries in acc["crontabs"].items():
        f.add("WARN", "host", f"crontab for `{user}`: {entries}.")
    ignore = tuple(base["recent_change_ignore"])
    critical = ("/etc/ssh", "/root/.ssh", "/etc/sudoers", "/etc/passwd", "/etc/shadow",
                "/etc/cron", "/var/spool/cron", "/etc/systemd/system")
    changed = [p for p in d["recent_changes"]["files"] if not p.startswith(ignore)]
    for p in changed:
        if p.startswith(critical):
            f.add("WARN", "host", f"security-relevant file changed in the window: {p}.")
    rest = [p for p in changed if not p.startswith(critical)]
    if rest:
        f.add("INFO", "host", f"{len(rest)} other files changed in the window: {rest[:15]}"
              + (" ..." if len(rest) > 15 else ""))
    units = [u for u in d["recent_changes"]["systemd_units"]
             if "/snap" not in u and "/apt-" not in u and not u.startswith(ignore)]
    for u in units:
        f.add("WARN", "host", f"systemd unit changed in the window: {u}.")
    for c in d["containers"]:
        if c["project"] != "fixflux":
            f.add("WARN", "host", f"container `{c['name']}` ({c['image']}) is not part of the "
                  "fixflux compose project.")
    env = d["env_file"]
    if not env.get("present"):
        f.add("ALERT", "secrets", "fixflux/.env is missing on the droplet.")
        return
    for name in base["required_env"]:
        if name not in env["names"]:
            f.add("ALERT", "secrets", f"`{name}` is not set in fixflux/.env.")
    if env["mode"] != "0o600":
        f.add("WARN", "secrets", f"fixflux/.env permissions are {env['mode']}, expected 0o600.")
    f.add("INFO", "secrets", f".env last modified {env['mtime']} (variables: {env['names']}).")


# ── report ───────────────────────────────────────────────────────────────────


def report(f: Findings, d: dict, ssh_sources: dict, open_ports: dict, host: str, days: int) -> str:
    out = [f"# FixFlux security audit - {d['hostname']}",
           f"Collected {d['collected_at']}, window: last {days} days.",
           "",
           f"**{f.count('ALERT')} ALERT, {f.count('WARN')} WARN, {f.count('INFO')} INFO**",
           ""]
    for sev in SEVERITIES:
        rows = [(a, m) for s, a, m in f.items if s == sev]
        if rows:
            out.append(f"## {sev}")
            out += [f"- **{a}**: {m}" for a, m in rows]
            out.append("")
    out.append("## SSH login sources (accepted)")
    by_class: dict[str, list] = defaultdict(list)
    for ip, (cls, n) in ssh_sources.items():
        by_class[cls].append((ip, n))
    out += [f"- {cls}: {sum(n for _, n in v)} login(s) from {len(v)} IP(s)"
            for cls, v in sorted(by_class.items())] or ["- none"]
    out.append("")
    if open_ports:
        out.append(f"## Ports reachable from this machine ({host})")
        reachable = [p for p, o in sorted(open_ports.items(), key=lambda kv: int(kv[0])) if o]
        out.append("- open: " + (", ".join(reachable) or "none"))
        out.append("")
    db = d["grafana_db"]
    if "users" in db:
        out.append("## Grafana accounts")
        out += [f"- id {u[0]} `{u[1]}` admin={bool(u[2])} disabled={bool(u[3])} created={u[4]} "
                f"last_seen={u[5]}" for u in db["users"]]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default=os.getenv("FIXFLUX_DROPLET_HOST"),
                    help="droplet IP/hostname (or FIXFLUX_DROPLET_HOST)")
    ap.add_argument("--key", default="~/.ssh/fixflux_do")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--json-out", help="also write the raw collected data here")
    ap.add_argument("--no-external", action="store_true", help="skip port probes and IP lookups")
    ap.add_argument("--from-json", help="analyse previously collected data (offline; implies "
                    "--no-external). For re-checking saved evidence and testing the checks.")
    args = ap.parse_args()
    if args.from_json:
        args.no_external = True
        args.host = args.host or "offline"
    if not args.host:
        ap.error("--host or FIXFLUX_DROPLET_HOST is required")

    base = json.loads((HERE / "baseline.json").read_text(encoding="utf-8"))
    if args.from_json:
        data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    else:
        data = collect_remote(args.host, args.key, args.days)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(data, indent=2), encoding="utf-8")

    my_ip = gh_nets = None
    open_ports: dict[str, bool] = {}
    if not args.no_external:
        my_ip = (fetch("https://api.ipify.org") or "").strip() or None
        gh_nets = github_actions_networks()
        ports = set(base["sensitive_ports"]) | set(base["accepted_public_ports"])
        ports |= {lst["port"] for lst in data["listeners"] if not is_internal(lst["host"])}
        open_ports = probe(args.host, sorted(ports, key=int))

    f = Findings()
    for name, fn in (("compose", lambda: check_compose(f)),
                     ("listeners", lambda: check_listeners(f, data, base, open_ports)),
                     ("external", lambda: check_external(f, open_ports, base)),
                     ("grafana", lambda: check_grafana(f, data, base, args.days)),
                     ("host", lambda: check_host(f, data, base, args.days))):
        try:
            fn()
        except (KeyError, TypeError) as exc:
            f.add("WARN", name, f"check could not run ({type(exc).__name__}: {exc}); "
                  "see the raw data with --json-out.")
    try:
        sources = check_ssh(f, data, base, my_ip, gh_nets)
    except (KeyError, TypeError) as exc:
        f.add("WARN", "ssh", f"check could not run ({type(exc).__name__}: {exc}).")
        sources = {}

    sys.stdout.write(report(f, data, sources, open_ports, args.host, args.days))
    return 2 if f.count("ALERT") else 1 if f.count("WARN") else 0


if __name__ == "__main__":
    sys.exit(main())
