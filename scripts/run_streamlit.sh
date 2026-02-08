#!/bin/bash

# Upsonic Streamlit Startup Script
# This script starts the Streamlit web interface for the Upsonic AI Agent

# Change to project directory
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/Scripts/activate
fi

# Start the Streamlit app
echo "Starting Upsonic Streamlit web interface..."
streamlit run apps/web/streamlit_app.py
