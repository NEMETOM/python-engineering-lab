# Start port-forwards for services not exposed via LoadBalancer.
# LoadBalancer services (trade-store :8000, compliance :8010, grafana :3000,
# postgres :5432/:5433, redpanda :9092) are already on localhost - no forwarding needed.
# Run from any directory. Press Ctrl+C to stop all forwards.
# Usage: .\scripts\k8s-port-forward.ps1

$NS = 'fix-simulator'

$forwards = @(
    @{ svc = 'prometheus';  local = 9090; remote = 9090 },
    @{ svc = 'fix-gateway'; local = 9878; remote = 9878 }
)

Write-Host "`nStarting port-forwards..." -ForegroundColor Cyan
$jobs = @()
foreach ($f in $forwards) {
    $jobs += Start-Job -ScriptBlock {
        param($ns, $svc, $local, $remote)
        kubectl port-forward -n $ns "svc/$svc" "${local}:${remote}"
    } -ArgumentList $NS, $f.svc, $f.local, $f.remote
    Write-Host "  localhost:$($f.local) -> $($f.svc):$($f.remote)"
}

Write-Host "`nLoadBalancer services (already on localhost, no forward needed):" -ForegroundColor DarkGray
Write-Host "  localhost:8000  -> trade-store API    (http://localhost:8000/docs)"
Write-Host "  localhost:8010  -> compliance API     (http://localhost:8010/docs)"
Write-Host "  localhost:3000  -> Grafana            (admin / admin)"
Write-Host "  localhost:9090  -> Prometheus         (forwarded above)"
Write-Host "  localhost:9092  -> Redpanda/Kafka"
Write-Host "  localhost:5433  -> PostgreSQL"

Write-Host "`nPress Ctrl+C to stop all port-forwards." -ForegroundColor Yellow

try {
    while ($true) {
        Start-Sleep -Seconds 5
        # Restart any job that died unexpectedly
        foreach ($i in 0..($jobs.Count - 1)) {
            if ($jobs[$i].State -eq 'Failed' -or $jobs[$i].State -eq 'Completed') {
                $f = $forwards[$i]
                Write-Host "  restarting $($f.svc) forward..." -ForegroundColor Yellow
                $jobs[$i] = Start-Job -ScriptBlock {
                    param($ns, $svc, $local, $remote)
                    kubectl port-forward -n $ns "svc/$svc" "${local}:${remote}"
                } -ArgumentList $NS, $f.svc, $f.local, $f.remote
            }
        }
    }
} finally {
    Write-Host "`nStopping port-forwards..." -ForegroundColor Cyan
    $jobs | Stop-Job
    $jobs | Remove-Job -Force
}
