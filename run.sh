#!/bin/bash
echo "🚀 Starting Annapradata Server..."
cd src && ../venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
