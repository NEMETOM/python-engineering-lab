# Kubernetes Cheat Sheet - FIXFlux
### Beginner's Guide

## 1. First-Time Setup (do this once)

### Enable Kubernetes in Docker Desktop
1. Open **Docker Desktop**
2. Click the gear icon (Settings)
3. Go to **Kubernetes**
4. Tick **Enable Kubernetes**
5. Click **Apply & Restart**
6. Wait ~2 minutes

### Verify it worked
```bash
kubectl version --client
kubectl get nodes
```
Expected output:
```
NAME             STATUS   ROLES           AGE   VERSION
docker-desktop   Ready    control-plane   ...   v1.xx.x
```

---

## 2. Key Concepts (plain English)

| Kubernetes term | What it is |
|---|---|
| **Pod** | A running container (or group of containers) - the smallest unit |
| **Deployment** | Manages pods - restarts them if they crash, handles scaling |
| **StatefulSet** | Like a Deployment but for stateful things (Redpanda, PostgreSQL) |
| **Service** | A stable address for reaching pods (like a DNS entry) |
| **ConfigMap** | A place to store config (env vars, YAML files) without rebuilding images |
| **Secret** | Like ConfigMap but for sensitive values (passwords) |
| **Namespace** | A logical group that isolates resources - ours is `fix-simulator` |
| **HPA** | Horizontal Pod Autoscaler - automatically adds/removes pods under load |

---

## 3. Docker Compose vs Kubernetes - Quick Comparison

| Task | Docker Compose | Kubernetes |
|---|---|---|
| Start full pipeline | `docker compose --profile full up --build` | `kubectl apply -k k8s/` |
| Start with monitoring | `docker compose --profile full --profile monitoring up` | Included in `kubectl apply -k k8s/` |
| Stop everything | `docker compose down` | `kubectl delete -k k8s/` |
| View logs | `docker compose logs -f fix-gateway` | `kubectl logs -n fix-simulator deploy/fix-gateway -f` |
| Restart a service | `docker compose restart fix-gateway` | `kubectl rollout restart -n fix-simulator deploy/fix-gateway` |
| Scale a service | Not supported (1 replica only) | `kubectl scale -n fix-simulator deploy/trade-store-api --replicas=3` |
| Access Trade Store API | `http://localhost:8000` directly | `kubectl port-forward -n fix-simulator svc/trade-store 8000:8000` first |
| Access Compliance API | `http://localhost:8010` directly | `kubectl port-forward -n fix-simulator svc/compliance-service 8010:8010` first |
| Access Grafana | `http://localhost:3000` directly | `kubectl port-forward -n fix-simulator svc/grafana 3000:3000` first |
| Update compliance rules | Edit YAML file + restart container | `kubectl edit configmap -n fix-simulator compliance-policies` (live) |
| Filedrop watcher | `python clients/fix-filedrop-client/watcher.py` | Same - always runs locally |
| Persist data across restarts | Named Docker volumes | PersistentVolumeClaims (automatic) |
| Auto-restart on crash | `restart: on-failure` | Built-in (always restarts) |
| Auto-scale under load | Not supported | HPA on matching engine (1-5 replicas) |

**When to use Docker Compose:** local development, quick iteration, running tests.

**When to use Kubernetes:** simulating production, testing scaling, HPA behaviour, or demonstrating the project to others.

---

## 4. Build Images (do this after every code change)

All images must be built from the `fixflux/` directory
so the Dockerfiles can copy the `shared/` folder.

```bash
cd fixflux

docker build -f services/fix-gateway/Dockerfile        -t fix-gateway:latest        .
docker build -f services/order-service/Dockerfile      -t order-service:latest      .
docker build -f services/matching-engine/Dockerfile    -t matching-engine:latest    .
docker build -f services/trade-store/Dockerfile        -t trade-store:latest        .
docker build -f services/compliance-service/Dockerfile -t compliance-service:latest .
docker build -f services/market-data-service/Dockerfile -t market-data-service:latest .
```

> **Tip:** With Docker Desktop's Kubernetes the images built locally are
> already visible to the cluster. No push to a registry needed.

---

## 5. Deploy the Full Stack

```bash
# Deploy everything (namespace, databases, all services)
kubectl apply -k k8s/

# Watch pods start up (Ctrl+C to stop watching)
kubectl get pods -n fix-simulator -w
```

Wait until all pods show `Running` or `1/1 Ready`.
Redpanda and PostgreSQL take the longest (~30-60 seconds).

---

## 6. Check What's Running

```bash
# See all pods and their status
kubectl get pods -n fix-simulator

# See all services (and their ports)
kubectl get services -n fix-simulator

# See everything at once
kubectl get all -n fix-simulator

# Check the HPA (auto-scaler) on the matching engine
kubectl get hpa -n fix-simulator
```

### What healthy output looks like
```
NAME                                    READY   STATUS    RESTARTS
postgres-0                              1/1     Running   0
redpanda-0                              1/1     Running   0
fix-gateway-xxx                         1/1     Running   0
order-service-xxx                       1/1     Running   0
matching-engine-xxx                     1/1     Running   0
trade-store-api-xxx                     1/1     Running   0
trade-store-consumer-xxx                1/1     Running   0
compliance-api-xxx                      1/1     Running   0
compliance-consumer-xxx                 1/1     Running   0
market-data-service-xxx                 1/1     Running   0
```

---

## 7. Access the APIs Locally

Kubernetes services are not directly accessible from your browser.
Use `port-forward` to map them to `localhost`:

```bash
# Trade Store API -> http://localhost:8000
kubectl port-forward -n fix-simulator svc/trade-store 8000:8000

# Compliance API -> http://localhost:8010
kubectl port-forward -n fix-simulator svc/compliance-service 8010:8010

# FIX Gateway TCP (for sending FIX messages directly) -> localhost:9878
kubectl port-forward -n fix-simulator svc/fix-gateway 9878:9878

# Grafana -> http://localhost:3000  (admin / admin)
kubectl port-forward -n fix-simulator svc/grafana 3000:3000

# Prometheus -> http://localhost:9090
kubectl port-forward -n fix-simulator svc/prometheus 9090:9090
```

Run each command in a separate terminal, then open:
- Trades: http://localhost:8000/trades
- Trade Store Swagger: http://localhost:8000/docs
- Violations: http://localhost:8010/violations
- Compliance Swagger: http://localhost:8010/docs
- Grafana dashboard: http://localhost:3000  (login: admin / admin)
- Prometheus targets: http://localhost:9090/targets

---

## 8. View Logs

```bash
# Follow logs from a service (like docker logs -f)
kubectl logs -n fix-simulator deploy/compliance-api -f
kubectl logs -n fix-simulator deploy/matching-engine -f
kubectl logs -n fix-simulator deploy/trade-store-consumer -f
kubectl logs -n fix-simulator deploy/order-service -f
kubectl logs -n fix-simulator deploy/fix-gateway -f

# See the last 50 lines without following
kubectl logs -n fix-simulator deploy/compliance-consumer --tail=50

# Logs from database services
kubectl logs -n fix-simulator statefulset/postgres --tail=30
kubectl logs -n fix-simulator statefulset/redpanda --tail=30
```

---

## 9. Drop a FIX Order File (Test the Pipeline)

The filedrop watcher runs locally (not in Kubernetes), so you still run it the usual way:

```bash
# Terminal 1 - start the filedrop watcher
pip install -e shared && pip install -e services/fix-gateway
python clients/fix-filedrop-client/watcher.py
```

```bash
# Terminal 2 - drop a test file
cp data/compliance_excessive_size.txt clients/fix-filedrop-client/filedrop/
```

The watcher publishes to Redpanda inside Kubernetes (accessible via the
service on port 9092). Then check the results:

```bash
# Port-forward first (in another terminal)
kubectl port-forward -n fix-simulator svc/trade-store 8000:8000
kubectl port-forward -n fix-simulator svc/compliance-service 8010:8010

# Then query
curl http://localhost:8000/trades | python -m json.tool
curl http://localhost:8010/violations | python -m json.tool
curl http://localhost:8010/risk | python -m json.tool
```

---

## 10. Update Compliance Rules (Without Rebuilding)

Compliance policies live in a ConfigMap - edit them live:

```bash
# Open the editor (uses your default terminal editor)
kubectl edit configmap -n fix-simulator compliance-policies
```

After saving, restart the consumers to reload the file:

```bash
kubectl rollout restart -n fix-simulator deploy/compliance-consumer
kubectl rollout restart -n fix-simulator deploy/compliance-api
```

---

## 11. Scale Services

```bash
# Scale trade-store API to 3 replicas (zero-downtime)
kubectl scale -n fix-simulator deploy/trade-store-api --replicas=3

# Scale back to 2
kubectl scale -n fix-simulator deploy/trade-store-api --replicas=2

# Check current replica count
kubectl get deploy -n fix-simulator trade-store-api

# See HPA auto-scaling status for matching engine
kubectl get hpa -n fix-simulator matching-engine
```

---

## 12. Restart a Service

Useful after rebuilding an image or changing a ConfigMap:

```bash
kubectl rollout restart -n fix-simulator deploy/compliance-api
kubectl rollout restart -n fix-simulator deploy/trade-store-api
kubectl rollout restart -n fix-simulator deploy/matching-engine

# Watch the restart progress
kubectl rollout status -n fix-simulator deploy/compliance-api
```

---

## 13. Troubleshoot a Crashing Pod

```bash
# Find which pods are not Running
kubectl get pods -n fix-simulator | grep -v Running

# Describe a pod - shows Events section with the actual failure reason
kubectl describe pod -n fix-simulator <pod-name>

# Get logs from a crashed pod (the previous run, before the restart)
kubectl logs -n fix-simulator <pod-name> --previous

# Get logs from a specific container inside a pod (multi-container pods)
kubectl logs -n fix-simulator <pod-name> -c <container-name> --previous
```

Common reasons a pod crashes:
- **CrashLoopBackOff** - the container keeps failing; check logs with `--previous`
- **Pending** - not enough resources or no node available
- **ImagePullBackOff** - image name wrong or not built yet; re-run `docker build`
- **Error** - application error on startup; check logs

### CrashLoopBackOff - clearing the exponential backoff

After many restarts Kubernetes applies exponential backoff (up to ~5 minutes between attempts).
Even after the root cause is fixed, pods can appear stuck for a long time.
Force an immediate retry for all deployments and statefulsets at once:

```bash
kubectl rollout restart deployment  -n fix-simulator
kubectl rollout restart statefulset -n fix-simulator
```

Or target a single service:

```bash
kubectl rollout restart -n fix-simulator deploy/trade-store-api
kubectl rollout restart -n fix-simulator statefulset/redpanda
```

### Check whether a service is actually reachable from localhost

```bash
# EXTERNAL-IP should show "localhost" for LoadBalancer services on Docker Desktop
# <none> means it is ClusterIP only - not reachable from outside the cluster
kubectl get svc -n fix-simulator
```

### Port-forward databases for local integration tests

Use this when your integration tests need a direct DB or broker connection and
the service is ClusterIP (no LoadBalancer):

```bash
# PostgreSQL - maps localhost:5433 -> cluster postgres:5432
kubectl port-forward -n fix-simulator svc/postgres 5433:5432

# Redpanda/Kafka - maps localhost:9092 -> cluster redpanda:9092
kubectl port-forward -n fix-simulator svc/redpanda 9092:9092
```

Run each in a separate terminal and keep it open while the tests run.

### Read the startup flags a running pod is actually using

```bash
# Shows the exact command + args the container was started with
kubectl get pod -n fix-simulator <pod-name> -o jsonpath='{.spec.containers[0].args}'
```

Useful to confirm a config change was actually applied to the cluster after `kubectl apply`.

---

## 14. Common kubectl Cheat Sheet

```bash
# Get everything in the namespace
kubectl get all -n fix-simulator

# Get detailed info about a specific resource
kubectl describe pod    -n fix-simulator <name>
kubectl describe deploy -n fix-simulator <name>
kubectl describe svc    -n fix-simulator <name>

# Delete and recreate a deployment (force redeploy)
kubectl rollout restart -n fix-simulator deploy/<name>

# Execute a command inside a running pod (like docker exec)
kubectl exec -it -n fix-simulator <pod-name> -- /bin/bash

# Copy a file into a pod
kubectl cp myfile.txt fix-simulator/<pod-name>:/tmp/myfile.txt

# Check resource usage (requires metrics-server)
kubectl top pods -n fix-simulator
kubectl top nodes
```

---

## 15. Tear Down

**Full reset - removes everything including old containers, volumes and data (recommended when finishing a session):**
```bash
kubectl delete namespace fix-simulator
```
All containers disappear from Docker Desktop within a few seconds.

**Soft stop - removes running pods but keeps data volumes (PostgreSQL trades, Prometheus metrics survive):**
```bash
kubectl delete -k k8s/
```

**Redeploy fresh after either option:**
```bash
kubectl apply -k k8s/
```
The namespace is recreated automatically on the next apply.

---

**PowerShell shortcuts - paste into your profile (`$PROFILE`) so you never have to remember the full commands:**

```powershell
function k8s-up   { kubectl apply -k C:\Dev\python-engineering-lab\fixflux\k8s\ }
function k8s-down { kubectl delete namespace fix-simulator }
```

Then from any terminal:
```powershell
k8s-up     # deploy everything
k8s-down   # tear down everything

Or just run the full command directly - no setup needed:
kubectl delete namespace fix-simulator
```

---

## 16. Starting Again After a Laptop Restart

When you restart your laptop Docker Desktop starts automatically, but the pods do not.
You need to redeploy - but whether you also need to rebuild depends on whether the images are still there.

**Step 1 - Check if images are still present (PowerShell):**
```powershell
docker images | Select-String "fix-gateway|order-service|matching-engine|trade-store|compliance|market-data"
```

- **All 6 images listed** - skip the build step, go straight to Step 2
- **Empty or missing images** - rebuild first (see Section 4), then go to Step 2

**Step 2 - Redeploy (no rebuild needed if images are present):**
```powershell
kubectl apply -k k8s/
```

**Step 3 - Watch pods come back up:**
```powershell
kubectl get pods -n fix-simulator -w
```

Wait until all pods show `1/1 Running`, then port-forward as normal (Section 7).

> Images survive laptop restarts because they are stored on disk by Docker.
> Only the running pods are lost when you shut down - the images are always reused.

---

## 17. Kubernetes Fails to Start (Docker Desktop)

Use this section when Docker Desktop shows Kubernetes as failed/yellow instead of green.

### Step 1 - Check if port 6443 is blocked by a foreign process

```powershell
netstat -ano | Select-String ":6443"
```

One entry is expected (Docker Desktop itself - `com.docker.backend`). If a different process owns the port:

```powershell
Get-Process -Id <PID>          # identify the process
Stop-Process -Id <PID> -Force  # kill it
```

Then retry: Docker Desktop Settings → Kubernetes → **Reset Kubernetes Cluster**.

### Step 2 - cgroup v2 conflict (most common cause on Windows 10 + WSL2)

**Symptom in logs:**
```
starting kubelet: waiting for [/sys/fs/cgroup/cpu/kubepods /sys/fs/cgroup/cpu/podruntime]: not all files found after 1m0s timeout
```

The kubelet expects cgroup v1 paths but the WSL2 kernel is running cgroup v2 unified hierarchy.

**Fix:** force cgroup v1 in WSL2. Open (or create) `%USERPROFILE%\.wslconfig`:

```powershell
notepad "$env:USERPROFILE\.wslconfig"
```

Add under a `[wsl2]` section:

```ini
[wsl2]
kernelCommandLine = systemd.unified_cgroup_hierarchy=0
```

Shut down WSL and restart Docker Desktop:

```powershell
wsl --shutdown
```

Wait 10 seconds, reopen Docker Desktop, wait for the green Docker icon, then Settings → Kubernetes → **Reset Kubernetes Cluster**.

### Step 3 - Read the actual failure reason from logs

```powershell
# Find the most recently written Docker Desktop logs
Get-ChildItem "$env:LOCALAPPDATA\Docker\log\host" -Filter "*.log" |
  Sort-Object LastWriteTime -Descending | Select-Object -First 5 | Select-Object FullName

# Search backend log for errors
Get-Content "$env:LOCALAPPDATA\Docker\log\host\com.docker.backend.exe.log" -Tail 60 |
  Select-String -Pattern "error|failed|kubelet|timeout" -CaseSensitive:$false
```

### Step 4 - Nuclear reset (last resort)

Docker Desktop → Troubleshoot (bug icon) → **Reset to factory defaults**

This removes all containers, images, and the Kubernetes cluster. Rebuild images afterwards (Section 4).

---

## 18. Risk Service (Pre-Trade Risk Checks)

The `risk-service` sits between `order-service` and `matching-engine` and enforces four MiFID II-aligned checks before any order reaches the book.

### Pipeline position

```
fix-gateway → raw_orders → order-service → validated_orders
                                                    ↓
                                             risk-service
                                            ↙           ↘
                               risk_approved_orders   risk_rejected_orders
                                        ↓
                                 matching-engine
```

### Four checks (evaluated in order, first failure stops)

| Check | Env var | Default | What it does |
|---|---|---|---|
| **Notional cap** | `RISK_NOTIONAL_LIMIT` | 1,000,000 | Rejects if `price × qty > limit` |
| **Fat-finger** | `RISK_FAT_FINGER_PCT` | 10.0 | Rejects if order price deviates >N% from last trade price. Skipped if no reference price exists yet. |
| **Gross / net position** | `RISK_GROSS_POSITION_LIMIT` / `RISK_NET_POSITION_LIMIT` | 10,000 / 5,000 | Rejects if adding this order would breach either limit. Position is tracked from filled trades (trades topic). |
| **Open order count** | `RISK_MAX_OPEN_ORDERS` | 10 | Rejects if the client already has this many unmatched orders outstanding. |

### State model

- Position state is **in-memory only** - replays from `trades` topic on startup (v1; Redis is a future option).
- `client_id` is sourced from FIX tag 49 (`SenderCompID`) and carried through `ValidatedOrderEvent`.

### Useful commands

```bash
# Check if risk-service is running
kubectl get pods -n fixflux -l app=risk-service

# Live logs (shows approved/rejected per order)
kubectl logs -n fixflux deploy/risk-service -f

# Override a limit without rebuilding (takes effect on next restart)
kubectl set env -n fixflux deploy/risk-service RISK_NOTIONAL_LIMIT=5000000

# Tail rejected orders
kubectl exec -n fixflux <redpanda-pod> -- \
  rpk topic consume risk_rejected_orders --offset start
```

For local development and BDD testing see the Testing section in [README.md](README.md).

---

## 19. PowerShell Helper Scripts

Scripts live in `scripts/` and can be run from any directory.

| Script | When to use it |
|---|---|
| `.\scripts\k8s-up.ps1` | Deploy the full stack and wait for all pods to be Ready |
| `.\scripts\k8s-down.ps1` | Full teardown - deletes namespace and all data volumes |
| `.\scripts\k8s-down.ps1 -Soft` | Soft stop - removes pods but keeps PVCs (PostgreSQL and Redpanda data survives) |
| `.\scripts\k8s-restart.ps1` | Clear CrashLoopBackOff backoff - restarts all deployments + statefulsets and auto-scales down stuck replicasets |
| `.\scripts\k8s-port-forward.ps1` | Start background port-forwards for services not on LoadBalancer (prometheus, fix-gateway). Press Ctrl+C to stop all. |
| `.\scripts\build-images.ps1` | Rebuild all seven Docker images after a code change |

### What's already on LoadBalancer (no port-forward needed)

| Service | localhost address |
|---|---|
| Trade Store API | http://localhost:8000/docs |
| Compliance API | http://localhost:8010/docs |
| Grafana | http://localhost:3000 (admin / admin) |
| PostgreSQL | localhost:5433 |
| Redpanda/Kafka | localhost:9092 |

---

## 20. Helm Alternative Commands

If you deployed with Helm instead of kubectl:

```bash
# Install
helm install fix-simulator ./helm/fixflux \
  --namespace fix-simulator --create-namespace

# See what's installed
helm list -n fix-simulator

# Upgrade after a code change
helm upgrade fix-simulator ./helm/fixflux \
  --namespace fix-simulator --set image.tag=latest

# Uninstall (removes everything including PVCs)
helm uninstall fix-simulator --namespace fix-simulator
kubectl delete namespace fix-simulator
```

---

## 21. Quick Reference Card

```
Deploy:           kubectl apply -k k8s/
Status:           kubectl get pods -n fix-simulator
Logs:             kubectl logs -n fix-simulator deploy/<service> -f
Crash logs:       kubectl logs -n fix-simulator <pod-name> --previous
Describe pod:     kubectl describe pod -n fix-simulator <pod-name>
API access:       kubectl port-forward -n fix-simulator svc/trade-store 8000:8000
DB access:        kubectl port-forward -n fix-simulator svc/postgres 5433:5432
Restart one:      kubectl rollout restart -n fix-simulator deploy/<service>
Restart all:      kubectl rollout restart deployment statefulset -n fix-simulator
Scale:            kubectl scale -n fix-simulator deploy/<service> --replicas=N
Edit rules:       kubectl edit configmap -n fix-simulator compliance-policies
Check services:   kubectl get svc -n fix-simulator
Tear down:        kubectl delete -k k8s/
```
