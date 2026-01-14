# Dockerfile
FROM python:3.11-slim

# Install only what's really needed for most C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Best cache pattern
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: you can keep this for CI/CD or when not using bind-mount
# COPY . .

# Good default (overridden in compose for dev anyway)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]