# Deploy the full fix-simulator stack and wait for all pods to be Ready.
# Run from any directory.
# Usage: .\scripts\k8s-up.ps1

$NS  = 'fix-simulator'
$K8S = Join-Path $PSScriptRoot '..\k8s'

Write-Host "`nDeploying stack from $K8S ..." -ForegroundColor Cyan
kubectl apply -k $K8S
if ($LASTEXITCODE -ne 0) { Write-Host "kubectl apply failed" -ForegroundColor Red; exit 1 }

Write-Host "`nWaiting for all pods to be Ready (timeout: 3 min)..." -ForegroundColor Cyan
kubectl wait pod --all -n $NS --for=condition=Ready --timeout=180s

Write-Host "`nFinal pod status:" -ForegroundColor Green
kubectl get pods -n $NS

Write-Host "`nServices (LoadBalancer endpoints accessible without port-forward):" -ForegroundColor Green
kubectl get svc -n $NS
