# Simple FastAPI Dockerfile (Legacy API)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_BASE_URL=http://ollama:11434/v1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pydantic

# Copy application code
COPY src/ ./src/
COPY apps/api/main.py ./apps/api/
COPY pyproject.toml ./

# Install Upsonic from source
RUN pip install -e .

# Expose port (8001 to avoid conflict with Gateway)
EXPOSE 8001

# Run the Simple API
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
