#!/bin/bash
# VETKA FastAPI Server
# Phase 39.8 - Production ready

echo ""
echo "  Starting VETKA FastAPI Server..."
echo "  Port: 5001"
echo "  Docs: http://localhost:5001/docs"
echo ""

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run with uvicorn
uvicorn main:socket_app --host 0.0.0.0 --port 5001 --reload
