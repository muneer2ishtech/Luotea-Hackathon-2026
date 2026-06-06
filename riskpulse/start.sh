#!/usr/bin/env bash
# Start RiskPulse. Default port 8090; override with PORT=9000 ./start.sh
set -euo pipefail
PORT="${PORT:-8090}"
cd "$(dirname "$0")/backend"
echo "Starting RiskPulse on http://localhost:${PORT}/riskpulse-no-ml"
exec python -m uvicorn main:app --reload --port "$PORT"
