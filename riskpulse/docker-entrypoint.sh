#!/bin/sh
set -eu

PORT="${PORT:-8090}"
cd /app/backend

echo "Preprocessing hackathon data from ${HACKATHON_DATA:-default path}..."
python preprocess.py

echo "Starting RiskPulse on http://0.0.0.0:${PORT}"
exec python -m uvicorn main:app --host 0.0.0.0 --port "$PORT"
