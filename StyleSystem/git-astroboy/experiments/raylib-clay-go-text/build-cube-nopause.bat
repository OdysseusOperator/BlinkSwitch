@echo off
echo ===============================================
echo Building 3D Cube Experiment
echo ===============================================
echo.

REM Change to the correct directory
cd /d "%~dp0"

echo Building executable...
go build -o cube-experiment.exe -ldflags="-s -w" cube-experiment.go

echo Copying required DLLs...
if exist raylib.dll (
    echo raylib.dll already present
) else (
    echo Warning: raylib.dll not found in directory
)

if %ERRORLEVEL% equ 0 (
    echo.
    echo BUILD SUCCESSFUL!
    echo Output: cube-experiment.exe
    echo.
    echo Run with: cube-experiment.exe
) else (
    echo.
    echo BUILD FAILED!
    echo Check the error messages above.
    exit /b 1
)
