@echo off
setlocal
title BlinkSwitch Clay Frontend
cd /d "%~dp0"

set "BLINKSWITCH_FRONTEND=clay"
call start.bat %*
exit /b %errorlevel%
