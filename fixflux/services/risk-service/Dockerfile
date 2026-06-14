FROM python:3.11-slim

WORKDIR /app

COPY services/risk-service/pyproject.toml .
COPY services/risk-service/src ./src
COPY shared ./shared

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["python", "-m", "risk_service.consumer"]
