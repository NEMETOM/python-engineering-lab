FROM python:3.11-slim

WORKDIR /app

COPY services/market-data-service/pyproject.toml .
COPY services/market-data-service/src ./src
COPY shared ./shared

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["python", "-m", "market_data_service.consumer"]
