#!/usr/bin/env bash
# Lanza la API Python (FastAPI) en el puerto 8000.
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then python3 install.py --no-run; fi
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
exec python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
