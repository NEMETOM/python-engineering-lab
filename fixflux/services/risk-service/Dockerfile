FROM python:3.11-slim

WORKDIR /app

COPY shared ./shared
RUN pip install --no-cache-dir \
    "opentelemetry-api>=1.24" \
    "opentelemetry-sdk>=1.24" \
    "opentelemetry-exporter-otlp-proto-http>=1.24"

COPY services/risk-service/pyproject.toml .
COPY services/risk-service/src ./src
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["python", "-m", "risk_service.consumer"]
