@echo off
echo Building AstroBoy4 Collision Test...
go build -o collision-test.exe main.go
if %errorlevel% equ 0 (
    echo Build successful! Run collision-test.exe to start.
    copy ..\raylib.dll . >nul 2>&1
    echo Copied raylib.dll
) else (
    echo Build failed!
    exit /b 1
)
