# Cloud Transition and Deployment Plan
## FIXFlux - DigitalOcean k3s

**Target:** DigitalOcean Premium Droplet - Ubuntu 24.04, 2 vCPUs, 4GB RAM, 80GB NVMe SSD  
**Orchestrator:** k3s v1.29+ (single-node)  
**Author:** Principal Cloud Architect blueprint - theoretical, no live execution

---

## Table of Contents

1. [Target Cloud Topology](#1-target-cloud-topology)
2. [Docker Compose to Kubernetes Migration](#2-docker-compose-to-kubernetes-migration)
3. [Prometheus and Grafana Observability via Helm](#3-prometheus-and-grafana-observability-via-helm)
4. [80GB Storage Safety Protocols](#4-80gb-storage-safety-protocols)
5. [Sequential Deployment Checklist](#5-sequential-deployment-checklist)

---

## 1. Target Cloud Topology

### 1.1 Infrastructure Overview

**Infrastructure layout** (what runs where):

```
  DigitalOcean Region (e.g. AMS3 or LON1)
  +------------------------------------------------------------------+
  |                                                                  |
  |  Droplet: fixflux-prod                                           |
  |  Ubuntu 24.04 LTS  |  2 vCPU  |  4 GB RAM  |  80 GB NVMe SSD   |
  |  Firewall: inbound 22 (SSH), 80/443 (HTTPS), 9878 (FIX TCP),    |
  |            30092 (Kafka NodePort)                                |
  |                                                                  |
  |  +------------------------------------------------------------+  |
  |  | k3s single-node cluster   (namespace: fixflux)             |  |
  |  |                                                            |  |
  |  |  -- Infrastructure tier -----------------------------------  |  |
  |  |  +-------------+  +-------------+  +--------------------+  |  |
  |  |  | Redpanda    |  | PostgreSQL  |  | Prometheus         |  |  |
  |  |  | StatefulSet |  | StatefulSet |  | + Grafana          |  |  |
  |  |  | 10 Gi PVC   |  | 5 Gi PVC    |  | 6 Gi PVC           |  |  |
  |  |  +-------------+  +-------------+  +--------------------+  |  |
  |  |                                                            |  |
  |  |  -- Application tier --------------------------------------  |  |
  |  |  +-------------+  +---------------+  +-----------------+  |  |
  |  |  | fix-gateway  |  | order-service |  | risk-service    |  |  |
  |  |  | port :9878   |  |               |  | (MiFID II)      |  |  |
  |  |  +-------------+  +---------------+  +-----------------+  |  |
  |  |                                                            |  |
  |  |  +------------------+  +------------------+               |  |
  |  |  | matching-engine  |  | market-data-     |               |  |
  |  |  | HPA (1-3)        |  | service          |               |  |
  |  |  +------------------+  +------------------+               |  |
  |  |                                                            |  |
  |  |  +--------------------+  +--------------------+           |  |
  |  |  | trade-store        |  | compliance-service |           |  |
  |  |  | api + consumer     |  | api + consumer     |           |  |
  |  |  | REST :8000         |  | REST :8010         |           |  |
  |  |  +--------------------+  +--------------------+           |  |
  |  |                                                            |  |
  |  |  -- Ingress (Traefik, k3s built-in) ----------------------  |  |
  |  |    /trades       -->  trade-store :8000        (HTTPS)     |  |
  |  |    /violations   -->  compliance-service :8010  (HTTPS)    |  |
  |  |    monitor.*     -->  grafana :3000             (HTTPS)    |  |
  |  +------------------------------------------------------------+  |
  |                                                                  |
  +------------------------------------------------------------------+

  DigitalOcean Container Registry (DOCR)
  registry.digitalocean.com/<your-org>/
  fix-gateway | order-service | risk-service | matching-engine
  trade-store | compliance-service | market-data-service
```

**Message flow** (how orders travel through the pipeline):

```
  FIX client (local machine or external)
        |
        |  TCP :9878
        v
  +-------------+
  | fix-gateway |   parses FIX protocol
  +-------------+
        |
        |  topic: raw_orders
        v
  +---------------+
  | order-service |   validates, enriches
  +---------------+
        |
        |  topic: validated_orders
        v
  +-----------------+
  |  risk-service   |   MiFID II pre-trade checks:
  |                 |   notional cap, fat-finger, position limits
  +-----------------+
        |           |
        | approved  |  rejected
        |           |
        v           +-----------> topic: risk_rejected_orders
        |                                |
        |  topic: risk_approved_orders   v
        |                         +-----------------+
        |                         | compliance-     |
        |                         | service         |
        v                         | (api+consumer)  |
  +------------------+            | REST :8010      |
  | matching-engine  |            +-----------------+
  | HPA (1-3)        |
  +------------------+
        |
        |  topic: matched_trades
        |
        +---------------------+---------------------+
        |                     |                     |
        v                     v                     v
  +-------------+    +-----------------+    +--------------------+
  | trade-store |    | compliance-     |    | market-data-       |
  | api+consumer|    | service         |    | service            |
  | REST :8000  |    | (also consumes  |    | (publishes price   |
  +-------------+    |  matched_trades)|    |  snapshots)        |
                     +-----------------+    +--------------------+
```
### 1.2 Droplet Sizing Analysis

| Resource | Available | Allocated (requests) | Allocated (limits) | Headroom |
|---|---|---|---|---|
| CPU | 2000m | ~1350m | ~6500m | Burst OK on single node |
| RAM | 4096Mi | ~2304Mi | ~3664Mi | ~430Mi OS+k3s overhead |
| NVMe SSD | 80GB | 21Gi PVCs | + images + OS | ~47GB free |

**RAM budget breakdown:**

| Component | Memory Limit |
|---|---|
| k3s (kubelet + containerd + flannel + traefik) | ~400Mi |
| OS (Ubuntu minimal) | ~300Mi |
| redpanda | 600Mi |
| postgres | 512Mi |
| matching-engine | 512Mi |
| compliance-api + compliance-consumer | 512Mi + 512Mi |
| prometheus | 512Mi |
| fix-gateway + order-service | 256Mi + 256Mi |
| trade-store-api + trade-store-consumer | 256Mi + 256Mi |
| market-data-service | 256Mi |
| risk-service | 256Mi |
| grafana | 256Mi |
| **Total** | **~5.7Gi** |

**The total limits slightly exceed physical RAM - this is normal for limit-based scheduling.** The key constraint is requests (~2.3Gi) which are well within the 4GB minus overhead (~3.4Gi usable). Kubernetes only evicts pods when the node is memory-pressured; limits are a ceiling per pod, not a reservation. The one risk is redpanda: if it approaches its 600Mi limit and other pods are also peaking simultaneously, the kernel OOM killer may intervene. See Section 2.3 for the mitigation.

### 1.3 k3s vs Full k8s: Why k3s

| Concern | k3s | Full k8s (kubeadm) |
|---|---|---|
| Install time | ~2 minutes (single binary) | 20-30 minutes |
| RAM overhead | ~400Mi (bundled containerd) | ~700-900Mi |
| etcd | SQLite by default | etcd required |
| Built-in ingress | Traefik pre-installed | Manual nginx-ingress |
| Compatibility with existing manifests | 100% - same API | 100% |

The existing `k8s/` kustomize manifests and `helm/fixflux/` chart deploy unmodified to k3s.

### 1.4 Network Exposure Strategy

On Docker Desktop, `LoadBalancer` type services expose on `localhost` automatically. On a real cloud node, `LoadBalancer` requires a cloud load balancer (billable, ~$12/mo each on DO). The replacement strategy for k3s:

| Local (Docker Desktop) | Cloud (k3s on DO) | Reason |
|---|---|---|
| `LoadBalancer` â†’ `localhost:8000` | `ClusterIP` + Traefik `IngressRoute` | No extra cost; HTTPS termination |
| `LoadBalancer` â†’ `localhost:9092` | `NodePort 30092` | Kafka protocol - not HTTP, can't use ingress |
| `LoadBalancer` â†’ `localhost:5433` | `ClusterIP` only | DB not public; connect via SSH tunnel |
| `LoadBalancer` â†’ `localhost:3000` | `ClusterIP` + Traefik `IngressRoute` | Grafana behind HTTPS |

---

## 2. Docker Compose to Kubernetes Migration

### 2.1 What Already Exists

The project has production-grade k8s artifacts ready:

- `k8s/` - kustomize base with all manifests (namespace, configmaps, secrets, all 12 services)
- `helm/fixflux/` - fully parameterized Helm chart with 13 templates
- `docker-compose.yml` - docker-compose with profiles (pipeline, full, monitoring) and log rotation

**Gap analysis: what the existing k8s/ does NOT have for cloud:**

| Missing | Impact | Solution |
|---|---|---|
| Image registry references | Images are `local:latest`, not pullable on remote node | Push to DOCR, update image fields |
| Ingress resources | No HTTP routing; relies on LoadBalancer | Add Traefik IngressRoutes |
| TLS termination | No HTTPS | cert-manager + Let's Encrypt |
| DigitalOcean-specific StorageClass | Uses default (Docker Desktop hostpath) | Use `do-block-storage` StorageClass |
| Resource limits tuned for 4GB node | Helm values show 2Gi for redpanda | Override with cloud-specific values |
| Secrets in plaintext YAML | `k8s/02-secret.yaml` has base64-encoded creds | Seal with kubeseal or use DO managed secrets |

### 2.2 Image Registry Setup

**Option A: DigitalOcean Container Registry (DOCR)**
- Free tier: 1 repository, 500MB storage
- Cost at scale: $5/mo for 5GB (sufficient for 6 images ~500MB total)

```bash
# Authenticate Docker to DOCR
doctl auth init
doctl registry login

# Tag and push (example for fix-gateway)
docker tag fix-gateway:latest registry.digitalocean.com/<your-org>/fix-gateway:latest
docker push registry.digitalocean.com/<your-org>/fix-gateway:latest
```

**Option B: GitHub Container Registry (GHCR)**
- Free for public repos; 500MB free for private
- Integrates naturally with GitHub Actions CI

For a single developer, GHCR is simpler (no extra CLI). DOCR is preferable if you want everything in one DO account.

### 2.3 Cloud-specific Helm Values Override

Create `helm/values-digitalocean.yaml` (this file does NOT exist yet - create it):

```yaml
# Override values for DigitalOcean k3s single-node deployment

image:
  registry: "registry.digitalocean.com/<your-org>"
  tag: "latest"
  pullPolicy: Always

# DigitalOcean block storage StorageClass
storageClass: "do-block-storage"

redpanda:
  resources:
    requests:
      cpu: 250m
      memory: 450Mi
    limits:
      cpu: 800m
      memory: 600Mi       # keep at 600Mi - proven working on 500MB-headroom node

postgres:
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 400m
      memory: 512Mi

matchingEngine:
  autoscaling:
    maxReplicas: 3        # cap at 3 on single node (was 5)

tradeStore:
  api:
    replicas: 1           # single replica on single node (was 2)

monitoring:
  prometheus:
    retention: "7d"       # keep 7 days - see Section 4 for why
    resources:
      limits:
        memory: 512Mi

# Ingress (Traefik, k3s default)
ingress:
  enabled: true
  host: "fixflux.yourdomain.com"   # replace with real domain or DO droplet IP
  tls: true
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
```

Deploy with:

```bash
helm upgrade --install fixflux ./helm/fixflux \
  --namespace fixflux \
  --create-namespace \
  -f helm/values-digitalocean.yaml
```

### 2.4 Secrets Management

The current `k8s/02-secret.yaml` stores base64-encoded credentials in plaintext YAML. **Do not commit production credentials.** Two approaches:

**Approach A - Manual kubeseal (recommended for single-node):**

```bash
# Install kubeseal CLI; install sealed-secrets controller into k3s
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml

# Encrypt the secret
kubeseal --format yaml < k8s/02-secret.yaml > k8s/02-secret.sealed.yaml
# Commit 02-secret.sealed.yaml; never commit 02-secret.yaml
```

**Approach B - DigitalOcean App Platform secrets (simpler but less portable):**  
Store creds as DO environment variables and inject via Helm `--set` at deploy time. No sealed-secrets controller needed.

### 2.5 Ingress and TLS Configuration

k3s ships with Traefik v2. Add these resources (not currently in `k8s/` or `helm/`):

**`helm/fixflux/templates/ingress.yaml` (new file concept):**

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: fixflux-http
  namespace: {{ .Values.namespace }}
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`{{ .Values.ingress.host }}`) && PathPrefix(`/trades`)
      kind: Rule
      services:
        - name: trade-store
          port: 8000
    - match: Host(`{{ .Values.ingress.host }}`) && PathPrefix(`/violations`)
      kind: Rule
      services:
        - name: compliance-service
          port: 8010
    - match: Host(`monitor.{{ .Values.ingress.host }}`)
      kind: Rule
      services:
        - name: grafana
          port: 3000
  tls:
    certResolver: letsencrypt
{{- end }}
```

**For Kafka external access** (NodePort - cannot use HTTP ingress):

```yaml
# In helm/fixflux/templates/redpanda.yaml, add a NodePort service:
apiVersion: v1
kind: Service
metadata:
  name: redpanda-external
  namespace: {{ .Values.namespace }}
spec:
  type: NodePort
  selector:
    app: redpanda
  ports:
    - name: kafka-external
      port: 29092
      targetPort: 29092
      nodePort: 30092   # accessible as <droplet-ip>:30092
```

Update `advertised_kafka_api` in the redpanda ConfigMap to advertise `<droplet-ip>:30092` instead of `localhost:9092`.

### 2.6 CI/CD Pipeline (GitHub Actions sketch)

```yaml
# .github/workflows/deploy.yml (concept - not yet created)
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Login to DOCR
        run: doctl registry login --expiry-seconds 600
        env:
          DIGITALOCEAN_ACCESS_TOKEN: ${{ secrets.DO_TOKEN }}
      - name: Build and push images
        run: |
          for svc in fix-gateway order-service risk-service matching-engine trade-store compliance-service market-data-service; do
            docker build -f services/$svc/Dockerfile \
              -t registry.digitalocean.com/${{ vars.DOCR_ORG }}/$svc:${{ github.sha }} \
              -t registry.digitalocean.com/${{ vars.DOCR_ORG }}/$svc:latest .
            docker push registry.digitalocean.com/${{ vars.DOCR_ORG }}/$svc --all-tags
          done

  deploy:
    needs: build-push
    runs-on: ubuntu-latest
    steps:
      - name: Set kubectl context
        run: doctl kubernetes cluster kubeconfig save fixflux-prod  # if using DOKS, else SSH
      - name: Helm upgrade
        run: |
          helm upgrade --install fixflux ./helm/fixflux \
            --namespace fixflux --create-namespace \
            -f helm/values-digitalocean.yaml \
            --set image.tag=${{ github.sha }} \
            --wait --timeout 5m
```

---

## 3. Prometheus and Grafana Observability via Helm

### 3.1 Stack Options

| Option | Pros | Cons |
|---|---|---|
| **kube-prometheus-stack** (community Helm chart) | NodeExporter, kube-state-metrics, AlertManager, pre-built dashboards | Heavyweight: ~800Mi RAM, complex to debug |
| **Custom Helm templates** (current approach in `helm/fixflux/`) | Minimal, already parameterized, existing dashboard JSON works | No node/cluster metrics |
| **Grafana Alloy + remote_write to Grafana Cloud** | Zero local storage, always-on | Requires Grafana Cloud account, data leaves your node |

**Recommendation:** Keep the existing custom templates for the initial cloud deployment. They already work, the dashboard JSON exists at `helm/fixflux/files/fix_simulator_overview.json`, and resource usage is predictable. Add `kube-state-metrics` as a single additional deployment when you need cluster-level metrics.

### 3.2 Prometheus Configuration for k3s

The existing `monitoring.yaml` scrape config targets services by name within the namespace - this works identically in k3s. No changes needed for the base scrape config.

**Add these jobs** to the prometheus ConfigMap for cloud-relevant metrics:

```yaml
# Add to prometheus-config ConfigMap in helm/fixflux/templates/monitoring.yaml
- job_name: node-exporter
  static_configs:
    - targets: ["node-exporter:9100"]   # add node-exporter DaemonSet

- job_name: redpanda-admin
  metrics_path: /public_metrics
  static_configs:
    - targets: ["redpanda:9644"]

- job_name: market-data-service
  static_configs:
    - targets: ["market-data-service:8002"]  # verify port

- job_name: risk-service
  static_configs:
    - targets: ["risk-service:8003"]  # verify port
```

### 3.3 Existing Grafana Dashboard Migration

The dashboard JSON at `helm/fixflux/files/fix_simulator_overview.json` (15KB) is already provisioned via the `grafana-dashboard-provider` ConfigMap. It survives Helm upgrades because the ConfigMap is versioned.

**One change required:** On cloud, Grafana runs behind Traefik. Grafana needs to know its public path:

```yaml
# In helm/values-digitalocean.yaml, add:
grafana:
  env:
    GF_SERVER_ROOT_URL: "https://monitor.{{ .Values.ingress.host }}"
    GF_SERVER_SERVE_FROM_SUB_PATH: "false"
```

### 3.4 Alerting

Add a `PrometheusRule` resource (not currently in the project) for the two highest-value alerts:

```yaml
# Alert 1: Redpanda partition lag (order pipeline stalling)
- alert: KafkaConsumerLag
  expr: kafka_consumer_group_lag > 1000
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Consumer group {{ $labels.group }} is lagging"

# Alert 2: Node memory pressure (critical on 4GB node)
- alert: NodeMemoryHigh
  expr: (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) < 0.15
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Less than 15% RAM available on the droplet"
```

Route alerts to your email via Grafana's built-in alerting (no AlertManager needed for a single node). Configure under Grafana > Alerting > Contact points with your `tomas.nemeth@dataddo.com` address.

### 3.5 Prometheus Retention and TSDB Size

On an 80GB disk, uncapped Prometheus TSDB will grow ~2-5GB/month at a 15s scrape interval across 12 targets. Set explicit retention:

```yaml
# In helm/values-digitalocean.yaml
monitoring:
  prometheus:
    retention: "15d"     # 15 days covers typical sprint; ~1.5GB
    retentionSize: "3GB" # hard cap regardless of age
```

This maps to the Prometheus `--storage.tsdb.retention.time=15d` and `--storage.tsdb.retention.size=3GB` flags, which the existing `monitoring.yaml` template should expose as Helm values.

---

## 4. 80GB Storage Safety Protocols

### 4.1 Disk Allocation Map

| Layer | Estimated Size | Notes |
|---|---|---|
| Ubuntu 24.04 OS | ~4GB | Minimal install |
| k3s binary + containerd | ~500MB | Single binary |
| Docker/containerd image cache | ~3-4GB | 6 app images ~80MB each + base images |
| postgres PVC | 5Gi | Trade and compliance data |
| redpanda PVC | 10Gi | Kafka topic segments (default retention) |
| prometheus PVC | 5Gi | Capped at 3GB used via retention |
| grafana PVC | 1Gi | Dashboard configs only |
| k3s system logs | ~500MB | With journald size cap |
| **Total allocated** | **~31GB** | |
| **Free headroom** | **~49GB** | |

The free headroom is healthy. The two growth vectors to watch are: (1) redpanda segment accumulation if topic retention is unconfigured, and (2) container image cache if you deploy many image tags.

### 4.2 Redpanda Topic Retention

Without explicit retention, Redpanda keeps all segments forever. Set retention via `rpk` after initial deployment:

```bash
# Set 24-hour retention and 1GB size cap on all pipeline topics
for topic in raw_orders validated_orders matched_trades compliance_results market_data; do
  rpk topic alter-config $topic \
    --set retention.ms=86400000 \
    --set retention.bytes=1073741824
done
```

Or configure in the redpanda ConfigMap under `redpanda.default_topic_replications` and add retention defaults:

```yaml
# In redpanda ConfigMap redpanda.yaml section:
redpanda:
  log_segment_size: 67108864         # 64MB segments
  compacted_log_segment_size: 67108864
  retention_bytes: 1073741824        # 1GB per partition default
  log_retention_ms: 86400000         # 24 hours default
```

### 4.3 Container Image Pruning CronJob

Old image tags accumulate as you deploy new versions. Add a CronJob to the cluster:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: image-pruner
  namespace: fixflux
spec:
  schedule: "0 3 * * 0"   # 03:00 UTC every Sunday
  jobTemplate:
    spec:
      template:
        spec:
          hostPID: true
          containers:
            - name: pruner
              image: docker:cli
              command:
                - sh
                - -c
                - |
                  # Remove images not referenced by any running container, older than 48h
                  docker image prune -af --filter "until=48h"
              volumeMounts:
                - name: docker-sock
                  mountPath: /var/run/docker.sock
          volumes:
            - name: docker-sock
              hostPath:
                path: /var/run/docker.sock
          restartPolicy: OnFailure
```

**Note:** On k3s, the runtime is containerd (not Docker). Replace `docker image prune` with `crictl rmi --prune` and mount the containerd socket at `/run/k3s/containerd/containerd.sock`.

### 4.4 Prometheus Log Cleanup CronJob

Prometheus's TSDB self-manages within the retention settings from Section 3.5. Supplement with a Kubernetes `CronJob` that monitors PVC usage and fires an alert if it crosses 80%:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: pvc-monitor
  namespace: fixflux
spec:
  schedule: "0 * * * *"   # every hour
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: monitor
              image: busybox:1.36
              command:
                - sh
                - -c
                - |
                  USED=$(df /prometheus | awk 'NR==2{print $5}' | tr -d '%')
                  if [ "$USED" -gt 80 ]; then
                    echo "ALERT: Prometheus PVC at ${USED}% - check retention settings"
                    exit 1
                  fi
                  echo "Prometheus PVC usage: ${USED}%"
              volumeMounts:
                - name: prometheus-data
                  mountPath: /prometheus
          volumes:
            - name: prometheus-data
              persistentVolumeClaim:
                claimName: prometheus-data
          restartPolicy: OnFailure
```

Pair this with the Prometheus alert from Section 3.4 for belt-and-suspenders coverage.

### 4.5 journald Log Cap (OS-level)

SSH into the droplet and configure journald to cap system logs at 500MB:

```bash
# /etc/systemd/journald.conf
[Journal]
SystemMaxUse=500M
SystemMaxFileSize=50M
MaxRetentionSec=7day
```

Then `systemctl restart systemd-journald`. k3s logs (kubelet, containerd) flow through journald and will be auto-rotated.

### 4.6 Disk Usage Monitoring Script

Deploy this as a systemd timer or cron entry on the droplet for a weekly summary email:

```bash
#!/bin/bash
# /usr/local/bin/disk-report.sh
THRESHOLD=70
USED=$(df / | awk 'NR==2{print $5}' | tr -d '%')

if [ "$USED" -gt "$THRESHOLD" ]; then
    echo "WARNING: root disk at ${USED}%" | \
    mail -s "fixflux-prod disk alert" tomas.nemeth@dataddo.com
fi
```

---

## 5. Sequential Deployment Checklist

Work through these phases in order. Do not proceed to the next phase if anything in the current phase fails.

---

### Phase 0: Pre-Flight (Local Machine)

- [ ] `doctl auth init` - authenticate DigitalOcean CLI with a personal access token
- [ ] `doctl registry create fixflux --region ams3` - create DOCR (or confirm it exists)
- [ ] `doctl registry login` - authorize Docker to push to DOCR
- [ ] Build all 7 application images locally (from `fixflux/`):
  ```bash
  for svc in fix-gateway order-service risk-service matching-engine trade-store compliance-service market-data-service; do
    docker build -f services/$svc/Dockerfile -t registry.digitalocean.com/<org>/$svc:latest .
  done
  ```
- [ ] Push images:
  ```bash
  for svc in fix-gateway order-service risk-service matching-engine trade-store compliance-service market-data-service; do
    docker push registry.digitalocean.com/<org>/$svc:latest
  done
  ```
- [ ] Verify images visible: `doctl registry repository list-tags <org>`
- [ ] Create `helm/values-digitalocean.yaml` with your DOCR org name and domain

---

### Phase 1: Droplet Provisioning

- [ ] Create droplet via DO console or CLI:
  ```bash
  doctl compute droplet create fixflux-prod \
    --region ams3 \
    --size s-2vcpu-4gb-intel \
    --image ubuntu-24-04-x64 \
    --ssh-keys <your-key-id> \
    --wait
  ```
- [ ] Note the droplet's public IP: `doctl compute droplet list`
- [ ] SSH in: `ssh root@<droplet-ip>`
- [ ] Update OS: `apt update && apt upgrade -y`
- [ ] Configure journald log cap (Section 4.5)
- [ ] Configure DO firewall to allow inbound 22, 80, 443, 9878, 30092

---

### Phase 2: k3s Installation

- [ ] Install k3s on the droplet:
  ```bash
  curl -sfL https://get.k3s.io | sh -s - \
    --write-kubeconfig-mode 644 \
    --disable servicelb \
    --disable traefik    # we'll install Traefik via Helm for version control
  ```
  **Note:** Disabling the bundled Traefik and servicelb so we control versions via Helm.
- [ ] Verify cluster is up: `kubectl get nodes` (should show `Ready`)
- [ ] Copy kubeconfig to local machine:
  ```bash
  scp root@<droplet-ip>:/etc/rancher/k3s/k3s.yaml ~/.kube/do-fixflux
  # Edit server: to https://<droplet-ip>:6443
  export KUBECONFIG=~/.kube/do-fixflux
  kubectl get nodes  # should work from local machine
  ```
- [ ] Install MetalLB or kube-vip for LoadBalancer support (optional - only if you want LoadBalancer type on non-DOKS):
  ```bash
  # Simpler alternative: skip LoadBalancer, use NodePort + Traefik as described in Section 1.4
  ```

---

### Phase 3: Cluster Prerequisites

- [ ] Create namespace:
  ```bash
  kubectl create namespace fixflux
  ```
- [ ] Link DOCR to k3s (so it can pull images):
  ```bash
  doctl registry kubernetes-manifest | kubectl apply -f -
  kubectl patch serviceaccount default -n fixflux \
    -p '{"imagePullSecrets": [{"name": "registry-fixflux"}]}'
  ```
- [ ] Install cert-manager (for TLS):
  ```bash
  helm repo add jetstack https://charts.jetstack.io
  helm install cert-manager jetstack/cert-manager \
    --namespace cert-manager --create-namespace \
    --set installCRDs=true
  ```
- [ ] Create Let's Encrypt ClusterIssuer:
  ```yaml
  # cluster-issuer.yaml (apply once)
  apiVersion: cert-manager.io/v1
  kind: ClusterIssuer
  metadata:
    name: letsencrypt-prod
  spec:
    acme:
      server: https://acme-v02.api.letsencrypt.org/directory
      email: tomas.nemeth@dataddo.com
      privateKeySecretRef:
        name: letsencrypt-prod
      solvers:
        - http01:
            ingress:
              class: traefik
  ```
  ```bash
  kubectl apply -f cluster-issuer.yaml
  ```
- [ ] Install Traefik via Helm:
  ```bash
  helm repo add traefik https://helm.traefik.io/traefik
  helm install traefik traefik/traefik \
    --namespace kube-system \
    --set service.type=NodePort \
    --set ports.web.nodePort=30080 \
    --set ports.websecure.nodePort=30443
  ```
- [ ] Point your domain's A record to `<droplet-ip>` and wait for DNS propagation: `dig +short fixflux.yourdomain.com`

---

### Phase 4: Infrastructure Tier (Stateful Services First)

Deploy stateful services and wait for them to be fully Ready before deploying application services.

- [ ] Apply secrets (using sealed or manual approach from Section 2.4):
  ```bash
  kubectl apply -f k8s/02-secret.yaml   # or sealed version
  ```
- [ ] Apply ConfigMaps:
  ```bash
  kubectl apply -f k8s/01-configmap.yaml
  kubectl apply -f k8s/redpanda.yaml  # redpanda-config ConfigMap only
  ```
- [ ] Deploy PostgreSQL:
  ```bash
  kubectl apply -f k8s/postgres.yaml
  kubectl wait --for=condition=Ready pod/postgres-0 -n fixflux --timeout=120s
  ```
- [ ] Verify PostgreSQL accepts connections:
  ```bash
  kubectl exec -n fixflux postgres-0 -- pg_isready -U fixuser -d fixdb
  ```
- [ ] Deploy Redpanda:
  ```bash
  kubectl apply -f k8s/redpanda.yaml
  kubectl wait --for=condition=Ready pod/redpanda-0 -n fixflux --timeout=180s
  ```
- [ ] Verify Redpanda is healthy:
  ```bash
  kubectl exec -n fixflux redpanda-0 -- rpk cluster info
  ```
- [ ] Set topic retention (Section 4.2):
  ```bash
  for topic in raw_orders validated_orders risk_approved_orders risk_rejected_orders matched_trades compliance_results market_data; do
    kubectl exec -n fixflux redpanda-0 -- rpk topic alter-config $topic \
      --set retention.ms=86400000 --set retention.bytes=1073741824
  done
  # 7 pipeline topics: validated_orders → risk-service → risk_approved_orders / risk_rejected_orders → matching-engine
  ```

---

### Phase 5: Application Tier

- [ ] Deploy all application services:
  ```bash
  # Either via kustomize with cloud overlay:
  kubectl apply -k k8s/

  # Or via Helm (preferred for cloud - parameterized):
  helm upgrade --install fixflux ./helm/fixflux \
    --namespace fixflux \
    -f helm/values-digitalocean.yaml \
    --wait --timeout 5m
  ```
- [ ] Watch pod startup:
  ```bash
  kubectl get pods -n fixflux -w
  ```
- [ ] Expected final state (all `1/1 Running`):
  ```
  postgres-0              1/1 Running
  redpanda-0              1/1 Running
  fix-gateway-xxx         1/1 Running
  order-service-xxx       1/1 Running
  risk-service-xxx        1/1 Running
  matching-engine-xxx     1/1 Running
  trade-store-api-xxx     1/1 Running
  trade-store-consumer-xxx 1/1 Running
  compliance-api-xxx      1/1 Running
  compliance-consumer-xxx 1/1 Running
  market-data-service-xxx 1/1 Running
  ```

---

### Phase 6: Observability Tier

- [ ] Deploy Prometheus and Grafana (included in Helm chart):
  ```bash
  # Already deployed with Phase 5 if monitoring is not in a separate profile
  kubectl get pods -n fixflux | grep -E "prometheus|grafana"
  ```
- [ ] Verify Prometheus targets are all `UP`:
  ```bash
  kubectl port-forward -n fixflux svc/prometheus 9090:9090
  # Open http://localhost:9090/targets
  ```
- [ ] Access Grafana via domain: `https://monitor.fixflux.yourdomain.com`
- [ ] Confirm `fix_simulator_overview` dashboard loads and panels show data
- [ ] Configure Grafana alert contact point with email (Section 3.4)
- [ ] Apply PrometheusRule for memory alert (Section 3.4)
- [ ] Deploy PVC monitor CronJob (Section 4.4)
- [ ] Deploy image pruner CronJob (Section 4.3)

---

### Phase 7: End-to-End Smoke Test

- [ ] Run the filedrop pipeline from your local machine (watcher connects to `<droplet-ip>:30092`):
  ```bash
  # Update watcher config or env to point to cloud Redpanda
  KAFKA_BROKER=<droplet-ip>:30092 python clients/fix-filedrop-client/watcher.py &
  cp data/compliance_excessive_size.txt clients/fix-filedrop-client/filedrop/
  ```
- [ ] Confirm trade appears in Trade Store API:
  ```bash
  curl https://fixflux.yourdomain.com/trades | python -m json.tool
  ```
- [ ] Confirm compliance violation appears:
  ```bash
  curl https://fixflux.yourdomain.com/violations | python -m json.tool
  ```
- [ ] Confirm Grafana dashboard shows non-zero order throughput
- [ ] Run integration tests against cloud endpoints:
  ```bash
  # In tests/integration/, update env vars to point to cloud
  TRADE_STORE_URL=https://fixflux.yourdomain.com \
  COMPLIANCE_URL=https://fixflux.yourdomain.com \
  KAFKA_BROKER=<droplet-ip>:30092 \
  DATABASE_URL="postgresql://fixuser:fixpass@<droplet-ip>:..." \
  make test-integration
  ```
- [ ] Verify all behave scenarios pass

---

### Phase 8: Post-Deployment Hardening

- [ ] Change Grafana admin password from default `admin`
- [ ] Rotate PostgreSQL password: update DO secret, `kubectl rollout restart` affected deployments
- [ ] Disable `auto_create_topics_enabled` in redpanda ConfigMap (was set to `true` for local dev; production should require explicit topic creation)
- [ ] Set `developer_mode: false` in redpanda ConfigMap and increase `--memory` to `600M`
- [ ] Configure weekly disk report script (Section 4.6) via `crontab -e` on the droplet
- [ ] Add droplet to DO monitoring and enable disk + memory alerts in DO console
- [ ] Document the droplet IP, DOCR org name, and Grafana URL in your team wiki

---

## Appendix: Resource Comparison

| Environment | Redpanda memory | API replicas | HPA max | Estimated monthly cost |
|---|---|---|---|---|
| Docker Desktop (local) | 320Mi | 1 | 5 | $0 |
| DO Droplet s-2vcpu-4gb | 600Mi | 1 | 3 | ~$24/mo |
| DO Droplet s-4vcpu-8gb | 2Gi | 2 | 5 | ~$48/mo |

The `s-2vcpu-4gb` tier is the minimum viable for this stack. Upgrading to `s-4vcpu-8gb` removes the memory constraint entirely and allows the Helm `values.yaml` defaults (2Gi Redpanda, 2x trade-store replicas) without modification.

---

*This document reflects the state of the codebase as of 2026-06-15. Verify StorageClass names, registry endpoints, and k3s version against current DigitalOcean documentation before executing.*
