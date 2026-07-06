#!/usr/bin/env bash
# Start HemaGuide backend (API + pre-built UI) on port 8001.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs

source /data/wilson_2/soft/miniforge3/etc/profile.d/conda.sh
conda activate hema_guide
export HEMAGUIDE_PYTHON=/data/wilson_2/conda/envs/hema_guide/bin/python

PORT="${HEMAGUIDE_PORT:-8001}"
HOST="${HEMAGUIDE_HOST:-0.0.0.0}"

if ss -tlnp | grep -q ":${PORT} "; then
  echo "Port ${PORT} already in use. Stop existing process first."
  exit 1
fi

nohup uvicorn backend.main:app --host "$HOST" --port "$PORT" >> "logs/backend-${PORT}.log" 2>&1 &
echo "Started HemaGuide on http://${HOST}:${PORT} (PID $!)"
echo "Health: curl http://127.0.0.1:${PORT}/api/health"
