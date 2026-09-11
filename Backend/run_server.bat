@echo off
setlocal
cd /d "%~dp0"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
