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

if not exist ".venv\Scripts\python.exe" (
    echo Creating the KyroX Python environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Could not create the Python environment.
        pause
        exit /b 1
    )
)

.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo Could not install backend dependencies. Check your internet connection and try again.
    pause
    exit /b 1
)

echo Starting KyroX backend at http://localhost:8000/
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
