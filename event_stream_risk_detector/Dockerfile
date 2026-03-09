FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY src ./src

# Install project in editable mode
RUN pip install -e .

# Default command
CMD ["python", "-m", "src.event_stream_risk_detector.consumer"]