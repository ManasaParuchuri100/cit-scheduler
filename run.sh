#!/bin/bash
# Start the CIT Scheduler website on http://localhost:8000
cd "$(dirname "$0")"
pip install -q -r requirements.txt --break-system-packages 2>/dev/null || pip install -q -r requirements.txt
exec python3 -m uvicorn cit.api:app --host 0.0.0.0 --port ${PORT:-8000}
