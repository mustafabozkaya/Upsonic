# Streamlit Gateway Client Dockerfile (Port 8502)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UPSONIC_API_KEY=dev-key-change-in-production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    streamlit \
    httpx \
    asyncio

# Copy application code
COPY apps/web/chat_client.py ./apps/web/

# Expose port (8502 to avoid conflict with simple client)
EXPOSE 8502

# Run Streamlit
CMD ["streamlit", "run", "apps/web/chat_client.py", "--server.port=8502", "--server.address=0.0.0.0"]
