FROM python:3.11-slim

WORKDIR /app

COPY services/matching-engine/pyproject.toml .
COPY services/matching-engine/src ./src
COPY shared ./shared

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["python", "-m", "matching_engine.consumer"]
