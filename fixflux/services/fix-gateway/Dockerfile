FROM python:3.11-slim

WORKDIR /app

COPY services/fix-gateway/pyproject.toml .
COPY services/fix-gateway/src ./src
COPY shared ./shared

# shared is copied in (not pip-installed), so its declared dependencies -
# including opentelemetry, used by shared/observability/tracing.py - are
# never resolved automatically. Install them explicitly, same as every
# other service that imports shared.observability.tracing.
RUN pip install --no-cache-dir \
    "opentelemetry-api>=1.24" \
    "opentelemetry-sdk>=1.24" \
    "opentelemetry-exporter-otlp-proto-http>=1.24"

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["python", "-m", "fix_gateway.server"]
