FROM python:3.11-slim

WORKDIR /app

COPY shared ./shared

COPY services/fix-injector/pyproject.toml .
COPY services/fix-injector/src ./src
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["uvicorn", "fix_injector.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
