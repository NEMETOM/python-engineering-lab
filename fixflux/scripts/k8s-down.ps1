# Tear down the fix-simulator stack.
# Run from any directory.
# Usage:
#   .\scripts\k8s-down.ps1          - full reset: deletes namespace + all data volumes
#   .\scripts\k8s-down.ps1 -Soft    - soft stop: removes pods but keeps PVCs (data survives)

param(
    [switch]$Soft
)

$NS  = 'fix-simulator'
$K8S = Join-Path $PSScriptRoot '..\k8s'

if ($Soft) {
    Write-Host "`nSoft stop — removing pods, keeping PVCs (data survives)..." -ForegroundColor Cyan
    kubectl delete -k $K8S
    if ($LASTEXITCODE -ne 0) { Write-Host "kubectl delete failed" -ForegroundColor Red; exit 1 }
    Write-Host "`nDone. Redeploy with: .\scripts\k8s-up.ps1" -ForegroundColor Green
} else {
    Write-Host "`nFull teardown — deleting namespace '$NS' and all volumes..." -ForegroundColor Cyan
    kubectl delete namespace $NS --ignore-not-found
    if ($LASTEXITCODE -ne 0) { Write-Host "kubectl delete namespace failed" -ForegroundColor Red; exit 1 }
    Write-Host "`nDone. Redeploy with: .\scripts\k8s-up.ps1" -ForegroundColor Green
}
