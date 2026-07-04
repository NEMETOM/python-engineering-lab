FROM python:3.11-slim

WORKDIR /app

COPY shared ./shared
RUN pip install --no-cache-dir \
    "opentelemetry-api>=1.24" \
    "opentelemetry-sdk>=1.24" \
    "opentelemetry-exporter-otlp-proto-http>=1.24"

COPY services/matching-engine/pyproject.toml .
COPY services/matching-engine/src ./src
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["python", "-m", "matching_engine.consumer"]
