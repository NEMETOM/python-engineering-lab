Set-Location (Split-Path $PSScriptRoot -Parent)

docker build -f services/fix-gateway/Dockerfile         -t fix-gateway:latest         .
docker build -f services/order-service/Dockerfile       -t order-service:latest       .
docker build -f services/matching-engine/Dockerfile     -t matching-engine:latest     .
docker build -f services/trade-store/Dockerfile         -t trade-store:latest         .
docker build -f services/compliance-service/Dockerfile  -t compliance-service:latest  .
docker build -f services/market-data-service/Dockerfile -t market-data-service:latest .
