@echo off
title Screeny - Window Switcher
cd %~dp0

REM Ensure Git LFS assets (fonts) are available before launching
echo Ensuring Git LFS assets are downloaded...
git lfs pull
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: git lfs pull failed; make sure Git LFS is installed or fonts may still be pointers.
)

echo Screeny - Window Switcher
echo ==========================

REM Ensure frontend virtual environment exists and is usable
if not exist frontend\.venv (
    echo Creating frontend virtual environment...
    python -m venv frontend\.venv
) else (
    if not exist frontend\.venv\Scripts\activate.bat (
        echo Frontend virtual environment is incomplete. Recreating...
        python -m venv --clear frontend\.venv
    )
)

REM Activate frontend virtual environment
call "frontend\.venv\Scripts\activate.bat"

REM Check if requirements are installed
echo Checking/installing frontend requirements...
pip install -q -r frontend\requirements.txt

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
