FROM python:3.11-slim

WORKDIR /app

COPY services/compliance-service/pyproject.toml .
COPY services/compliance-service/src ./src
COPY services/compliance-service/policies ./policies
COPY shared ./shared

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["uvicorn", "compliance_service.api.main:app", "--host", "0.0.0.0", "--port", "8010"]
