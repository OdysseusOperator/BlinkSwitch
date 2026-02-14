@echo off
title Screeny - Screen Assign Service
cd %~dp0

echo Screeny - ScreenAssign Service
echo ================================

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

REM Start ScreenAssign service
echo Starting ScreenAssign service on 127.0.0.1:5555...
python -m backend.backend

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred. Press any key to exit...
    pause > nul
)
