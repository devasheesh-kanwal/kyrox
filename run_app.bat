@echo off
setlocal
cd /d "%~dp0"

if not exist "Backend\run_server.bat" (
    echo KyroX backend launcher was not found.
    pause
    exit /b 1
)
if not exist "Frontend\run_frontend.bat" (
    echo KyroX frontend launcher was not found.
    pause
    exit /b 1
)

start "KyroX Backend" cmd /k call "%~dp0Backend\run_server.bat"
start "KyroX Frontend" cmd /k call "%~dp0Frontend\run_frontend.bat"

rem Give the frontend server a moment before opening the browser.
timeout /t 2 /nobreak >nul
start "" "http://localhost:5500/index.html"
