FROM python:3.11-slim

WORKDIR /app

COPY shared ./shared

COPY services/market-data-api/pyproject.toml .
COPY services/market-data-api/src ./src
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["uvicorn", "market_data_api.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
