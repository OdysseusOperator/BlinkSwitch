@echo off
title Screeny - Window Switcher
cd %~dp0

echo Screeny - Window Switcher
echo ==========================

REM Check if virtual environment exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if requirements are installed
echo Checking/installing requirements...
pip install -q -r requirements.txt

REM Wait for ScreenAssign backend to be ready
echo Waiting for ScreenAssign backend (127.0.0.1:5555) to be ready...
set MAX_RETRIES=30
set RETRY_COUNT=0

:CHECK_BACKEND
set /a RETRY_COUNT+=1
if %RETRY_COUNT% GTR %MAX_RETRIES% (
    echo ERROR: Backend did not start within 30 seconds!
    echo Please check if the ScreenAssign service is running.
    pause
    exit /b 1
)

REM Use curl to check health endpoint (available on Windows 10+)
curl -s -f -m 1 http://127.0.0.1:5555/screenassign/health >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Backend is ready!
    goto START_SWITCHER
)

REM Show progress indicator
echo Waiting... (attempt %RETRY_COUNT%/%MAX_RETRIES%)
timeout /t 1 /nobreak > nul
goto CHECK_BACKEND

:START_SWITCHER
REM Start Window Switcher
echo Starting Window Switcher...
echo Controls: Alt+Space to toggle, Up/Down to navigate, Enter to select, Esc to hide
echo.
python -m frontend.frontend-switcher

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred. Press any key to exit...
    pause > nul
)
