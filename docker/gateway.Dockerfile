# Upsonic AI Gateway API Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UPSONIC_API_KEY=dev-key-change-in-production
# Host makinedeki Ollama'ya bağlan (docker-compose'da override edilecek)
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434/v1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pydantic \
    python-dotenv

# Copy application code
COPY src/ ./src/
COPY apps/api/gateway.py ./apps/api/

# Install Upsonic from source
RUN pip install -e .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the Gateway API
CMD ["uvicorn", "apps.api.gateway:app", "--host", "0.0.0.0", "--port", "8000"]
