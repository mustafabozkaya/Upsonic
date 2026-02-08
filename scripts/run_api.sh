#!/bin/bash

# Upsonic API Startup Script
# This script starts the FastAPI server for the Upsonic AI Agent

# Change to project directory
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/Scripts/activate
fi

# Start the FastAPI server
echo "Starting Upsonic API server..."
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
