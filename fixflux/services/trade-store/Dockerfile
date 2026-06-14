FROM python:3.11-slim

WORKDIR /app

COPY services/trade-store/pyproject.toml .
COPY services/trade-store/src ./src
COPY shared ./shared

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["uvicorn", "trade_store.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
