@echo off
setlocal enabledelayedexpansion
title PROSPECT - Software Project Risk Analyzer
cd /d "%~dp0"

echo ============================================================
echo  PROSPECT - Predictive Software Project Risk ^& Engineering
echo  Control System - Windows Setup ^& Launcher
echo ============================================================
echo.

REM ----------------------------------------------------------------
REM 1. Check prerequisites
REM ----------------------------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH. Install Python 3.10+ from
    echo         https://www.python.org/downloads/ and re-run this script.
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js was not found on PATH. Install Node.js 18+ from
    echo         https://nodejs.org/ and re-run this script.
    pause
    exit /b 1
)

REM ----------------------------------------------------------------
REM 2. Backend: create venv, install dependencies
REM ----------------------------------------------------------------
echo [1/4] Setting up backend (Python virtual environment)...
cd backend
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies.
    pause
    exit /b 1
)
cd ..

REM ----------------------------------------------------------------
REM 3. Frontend: install npm dependencies
REM ----------------------------------------------------------------
echo [2/4] Setting up frontend (npm dependencies)...
cd frontend
if not exist node_modules (
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies.
        pause
        exit /b 1
    )
)
cd ..

REM ----------------------------------------------------------------
REM 4. Launch backend and frontend in separate windows
REM ----------------------------------------------------------------
echo [3/4] Starting backend API on http://127.0.0.1:8000 ...
start "PROSPECT Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && uvicorn app.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo [4/4] Starting frontend on http://127.0.0.1:5173 ...
start "PROSPECT Frontend (Vite)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo ============================================================
echo  PROSPECT is starting up in two new windows:
echo    Backend API : http://127.0.0.1:8000/api/health
echo    Frontend UI : http://127.0.0.1:5173
echo  Opening the app in your default browser...
echo ============================================================
start http://127.0.0.1:5173

endlocal
