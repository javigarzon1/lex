@echo off
REM Lanza la API Python (FastAPI) en el puerto 8000.
cd /d %~dp0
if not exist .venv ( python install.py --no-run )
call .venv\Scripts\activate
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
