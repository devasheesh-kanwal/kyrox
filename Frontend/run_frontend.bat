@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
    echo Make sure "Add Python to PATH" is selected during installation.
    pause
    exit /b 1
)

echo Starting KyroX frontend at http://localhost:5500/
python -m http.server 5500
