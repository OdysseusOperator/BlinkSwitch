@echo off
setlocal
echo Building Clay + Raylib dashboard...
go build -o clay-raylib-dashboard.exe .
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)
echo Build successful. Run with run.bat
