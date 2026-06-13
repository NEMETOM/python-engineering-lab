# Force-restart all deployments and statefulsets in fix-simulator.
# Use this to clear CrashLoopBackOff exponential backoff after fixing a root cause.
# Also detects and scales down stuck old replicasets that are blocking a rollout.
# Run from any directory.
# Usage: .\scripts\k8s-restart.ps1

$NS = 'fix-simulator'

Write-Host "`nRestarting all deployments..." -ForegroundColor Cyan
kubectl rollout restart deployment -n $NS

Write-Host "Restarting all statefulsets..." -ForegroundColor Cyan
kubectl rollout restart statefulset -n $NS

# Scale down any old replicasets still holding replicas (causes lock conflicts e.g. Prometheus)
$stuckRS = kubectl get replicaset -n $NS -o json |
    ConvertFrom-Json |
    Select-Object -ExpandProperty items |
    Where-Object { $_.spec.replicas -gt 0 -and $_.status.readyReplicas -eq 0 -and $_.metadata.ownerReferences }

if ($stuckRS) {
    Write-Host "`nScaling down stuck replicasets..." -ForegroundColor Yellow
    foreach ($rs in $stuckRS) {
        $name = $rs.metadata.name
        Write-Host "  scaling down $name"
        kubectl scale replicaset $name -n $NS --replicas=0
    }
}

Write-Host "`nWaiting for pods to settle (timeout: 3 min)..." -ForegroundColor Cyan
kubectl wait pod --all -n $NS --for=condition=Ready --timeout=180s

Write-Host "`nFinal pod status:" -ForegroundColor Green
kubectl get pods -n $NS
