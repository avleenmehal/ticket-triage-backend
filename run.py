#!/usr/bin/env python3
"""
Simple script to run the FastAPI server.
Usage: python run.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,        # Default port
        reload=False,     # Set to True for development
        log_level="info"
    )
