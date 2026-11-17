#!/usr/bin/env bash
# Preserve evidence on the FixFlux droplet BEFORE any containment step.
#
#   ssh -i ~/.ssh/fixflux_do root@<droplet> 'bash -s' < collect_evidence.sh
#
# Writes only to a new /root/incident-<UTC timestamp>/ (mode 700) and changes
# nothing else. Run it before recreating a container: `docker compose up`,
# `down`, a deploy, or a volume wipe erases that container's logs for good.
# Contains secrets (grafana.db, a copy of .env): never copy it into the repo.
set -uo pipefail

E=/root/incident-$(date -u +%Y%m%d-%H%M)
mkdir -p "$E" && chmod 700 "$E"
cd ~/python-engineering-lab/fixflux || exit 1

# Grafana: consistent DB snapshot (sqlite backup API, read-only source), logs, config.
G=$(docker ps -q --filter label=com.docker.compose.service=grafana)
if [ -n "$G" ]; then
  SRC=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/grafana"}}{{.Source}}{{end}}{{end}}' "$G")
  python3 -c "import sqlite3,sys; s=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close()" \
    "$SRC/grafana.db" "$E/grafana.db"
  docker logs --timestamps "$G" > "$E/grafana-container.log" 2>&1
  docker inspect "$G" > "$E/grafana-inspect.json"
fi

# Every other container's logs too: any of them may be the next one recreated.
mkdir -p "$E/container-logs"
for c in $(docker ps -a --format '{{.Names}}'); do
  docker logs --timestamps "$c" > "$E/container-logs/$c.log" 2>&1
done

# Access: SSH, logins, keys, accounts.
journalctl _COMM=sshd --since "30 days ago" --no-pager -o short-iso > "$E/sshd-journal.log" 2>&1
cp -a /var/log/auth.log* "$E/" 2>/dev/null
last -Fwi > "$E/last.txt" 2>&1; lastb -Fwi > "$E/lastb.txt" 2>&1; who -a > "$E/who.txt"
cp /root/.bash_history "$E/root-bash_history" 2>/dev/null
getent passwd > "$E/passwd.txt"; cp /etc/group "$E/" 2>/dev/null
cp /etc/sudoers "$E/" 2>/dev/null; ls -la /etc/sudoers.d > "$E/sudoers.d.txt" 2>&1
for h in /root /home/*; do
  [ -f "$h/.ssh/authorized_keys" ] && { echo "== $h"; stat -c '%y' "$h/.ssh/authorized_keys"; ssh-keygen -lf "$h/.ssh/authorized_keys"; }
done > "$E/authorized_keys.txt" 2>&1

# Persistence: cron, systemd, recently changed files.
{ for u in $(cut -d: -f1 /etc/passwd); do c=$(crontab -l -u "$u" 2>/dev/null) && echo "== $u" && echo "$c"; done
  ls -la /etc/cron.* /var/spool/cron/crontabs 2>/dev/null; } > "$E/cron.txt"
find /etc /root /home /usr/local /opt /var/spool/cron /tmp /var/tmp -xdev -type f -mtime -7 2>/dev/null \
  | grep -v "^$E" > "$E/files-changed-7d.txt"
find /etc/systemd /lib/systemd/system -xdev -type f -mtime -30 > "$E/systemd-changed-30d.txt" 2>/dev/null

# Runtime state.
ps auxwwf > "$E/ps.txt"; ss -tulpn > "$E/listening.txt"
docker ps -a --no-trunc > "$E/docker-ps.txt"; docker images --digests > "$E/docker-images.txt"
cp -a .env "$E/dotenv.copy" 2>/dev/null; cp -a docker-compose.yml "$E/"
git -C .. log -5 --format='%h %ci %s' > "$E/git-head.txt"; git -C .. status --short > "$E/git-status.txt"

(cd "$E" && find . -type f ! -name SHA256SUMS -exec sha256sum {} + > SHA256SUMS)
chmod -R go-rwx "$E"
echo "evidence: $E ($(find "$E" -type f | wc -l) files, $(du -sh "$E" | cut -f1))"
