# Streamlit Simple Client Dockerfile (Port 8501)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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
COPY apps/web/streamlit_app.py ./apps/web/

# Expose port (8501 standard Streamlit port)
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "apps/web/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
