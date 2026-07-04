FROM python:3.11-slim

WORKDIR /app

COPY shared ./shared
RUN pip install --no-cache-dir \
    "opentelemetry-api>=1.24" \
    "opentelemetry-sdk>=1.24" \
    "opentelemetry-exporter-otlp-proto-http>=1.24"

COPY services/trade-store/pyproject.toml .
COPY services/trade-store/src ./src
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["uvicorn", "trade_store.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
