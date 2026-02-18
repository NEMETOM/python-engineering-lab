# ----------------------------
# Base Image
# ----------------------------
FROM python:3.11-slim

# ----------------------------
# Environment
# ----------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ----------------------------
# Work directory
# ----------------------------
WORKDIR /app

# ----------------------------
# Install dependencies
# ----------------------------
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------
# Copy project
# ----------------------------
COPY . .

# ----------------------------
# Default command
# ----------------------------
ENTRYPOINT ["python", "cli.py"]
