@echo off
setlocal
echo Building BlinkSwitch Clay frontend...
go build -o blinkswitch-frontend.exe .
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)
echo Build successful.
