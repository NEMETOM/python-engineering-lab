FROM python:3.11-slim

WORKDIR /app

COPY services/fix-gateway/pyproject.toml .
COPY services/fix-gateway/src ./src
COPY shared ./shared

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["python", "-m", "fix_gateway.server"]
