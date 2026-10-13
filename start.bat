@echo off
setlocal
title BlinkSwitch
cd /d "%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
    echo ERROR: uv is required; install it from https://docs.astral.sh/uv/
    exit /b 1
)

set "BLINKSWITCH_VENV=%~dp0.venv-uv"

if not exist "%BLINKSWITCH_VENV%\Scripts\python.exe" (
    echo Creating shared Python environment...
    uv venv "%BLINKSWITCH_VENV%" --python 3.11
    if errorlevel 1 exit /b 1
)

"%BLINKSWITCH_VENV%\Scripts\python.exe" "scripts\start_blinkswitch.py" %*
exit /b %errorlevel%
