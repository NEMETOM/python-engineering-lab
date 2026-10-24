FROM python:3.11-slim

WORKDIR /app

COPY clients/fix-replay/pyproject.toml .
COPY clients/fix-replay/src ./src
COPY shared ./shared

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "fix_replay"]
