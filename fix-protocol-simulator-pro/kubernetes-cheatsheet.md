# Kubernetes Cheat Sheet - FIX Protocol Simulator Pro
### Beginner's Guide

Personal reference - not committed to the repository.

---

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

## 3. Build Images (do this after every code change)

All images must be built from the `fix-protocol-simulator-pro/` directory
so the Dockerfiles can copy the `shared/` folder.

```bash
cd fix-protocol-simulator-pro

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

## 4. Deploy the Full Stack

```bash
# Deploy everything (namespace, databases, all services)
kubectl apply -k k8s/

# Watch pods start up (Ctrl+C to stop watching)
kubectl get pods -n fix-simulator -w
```

Wait until all pods show `Running` or `1/1 Ready`.
Redpanda and PostgreSQL take the longest (~30-60 seconds).

---

## 5. Check What's Running

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

## 6. Access the APIs Locally

Kubernetes services are not directly accessible from your browser.
Use `port-forward` to map them to `localhost`:

```bash
# Trade Store API -> http://localhost:8000
kubectl port-forward -n fix-simulator svc/trade-store 8000:8000

# Compliance API -> http://localhost:8010
kubectl port-forward -n fix-simulator svc/compliance-service 8010:8010

# FIX Gateway TCP (for sending FIX messages directly) -> localhost:9878
kubectl port-forward -n fix-simulator svc/fix-gateway 9878:9878
```

Run each command in a separate terminal, then open:
- Trades: http://localhost:8000/trades
- Trade Store Swagger: http://localhost:8000/docs
- Violations: http://localhost:8010/violations
- Compliance Swagger: http://localhost:8010/docs

---

## 7. View Logs

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

## 8. Drop a FIX Order File (Test the Pipeline)

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

## 9. Update Compliance Rules (Without Rebuilding)

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

## 10. Scale Services

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

## 11. Restart a Service

Useful after rebuilding an image or changing a ConfigMap:

```bash
kubectl rollout restart -n fix-simulator deploy/compliance-api
kubectl rollout restart -n fix-simulator deploy/trade-store-api
kubectl rollout restart -n fix-simulator deploy/matching-engine

# Watch the restart progress
kubectl rollout status -n fix-simulator deploy/compliance-api
```

---

## 12. Troubleshoot a Crashing Pod

```bash
# Find which pods are not Running
kubectl get pods -n fix-simulator | grep -v Running

# Describe a pod to see events and error messages
kubectl describe pod -n fix-simulator <pod-name>

# Get logs from a crashed pod (previous run)
kubectl logs -n fix-simulator <pod-name> --previous
```

Common reasons a pod crashes:
- **CrashLoopBackOff** - the container keeps failing; check logs with `--previous`
- **Pending** - not enough resources or no node available
- **ImagePullBackOff** - image name wrong or not built yet; re-run `docker build`
- **Error** - application error on startup; check logs

---

## 13. Common kubectl Cheat Sheet

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

## 14. Tear Down

```bash
# Remove all project resources (keeps the namespace)
kubectl delete -k k8s/

# Remove everything including the namespace and PVCs (full reset)
kubectl delete namespace fix-simulator
```

Redeploy fresh:
```bash
kubectl apply -k k8s/
```

---

## 15. Helm Alternative Commands

If you deployed with Helm instead of kubectl:

```bash
# Install
helm install fix-simulator ./helm/fix-simulator-pro \
  --namespace fix-simulator --create-namespace

# See what's installed
helm list -n fix-simulator

# Upgrade after a code change
helm upgrade fix-simulator ./helm/fix-simulator-pro \
  --namespace fix-simulator --set image.tag=latest

# Uninstall (removes everything including PVCs)
helm uninstall fix-simulator --namespace fix-simulator
kubectl delete namespace fix-simulator
```

---

## 16. Quick Reference Card

```
Deploy:      kubectl apply -k k8s/
Status:      kubectl get pods -n fix-simulator
Logs:        kubectl logs -n fix-simulator deploy/<service> -f
API access:  kubectl port-forward -n fix-simulator svc/trade-store 8000:8000
Restart:     kubectl rollout restart -n fix-simulator deploy/<service>
Scale:       kubectl scale -n fix-simulator deploy/<service> --replicas=N
Edit rules:  kubectl edit configmap -n fix-simulator compliance-policies
Tear down:   kubectl delete -k k8s/
```
