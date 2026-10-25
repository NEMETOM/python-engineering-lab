FROM python:3.11-slim

WORKDIR /app

COPY shared ./shared
RUN pip install --no-cache-dir \
    "opentelemetry-api>=1.24" \
    "opentelemetry-sdk>=1.24" \
    "opentelemetry-exporter-otlp-proto-http>=1.24"

COPY services/reporting-service/pyproject.toml .
COPY services/reporting-service/src ./src
COPY services/reporting-service/reference ./reference
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["python", "-m", "reporting_service.consumer"]
