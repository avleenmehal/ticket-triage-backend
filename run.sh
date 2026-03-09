#!/bin/bash
# Simple bash script to run the FastAPI server
# Usage: ./run.sh

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
