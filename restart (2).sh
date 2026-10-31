#!/bin/bash
# stop any running server on port 8000, then start a fresh one
cd "$(dirname "$0")"
PID=$(lsof -ti tcp:8000 2>/dev/null || true); [ -n "$PID" ] && kill $PID && sleep 1
nohup python3 -m uvicorn cit.api:app --host 0.0.0.0 --port 8000 > "${1:-/tmp/cit-server.log}" 2>&1 &
sleep 4
