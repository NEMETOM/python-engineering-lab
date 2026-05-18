FROM python:3.11-slim

WORKDIR /app

COPY services/order-service/pyproject.toml .
COPY services/order-service/src ./src
COPY shared ./shared

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["python", "-m", "order_service.consumer"]
