@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo Building AstroBoy4 - Advanced Asteroids Game
echo ===============================================
echo.

REM Change to the correct directory
cd /d "%~dp0"

echo Building executable...
echo.
go build -v -o astroboy4.exe . 2>&1

REM Check if build succeeded
if errorlevel 1 goto :build_failed

REM Build successful
echo.
echo ===============================================
echo BUILD SUCCESSFUL!
echo ===============================================
echo.

REM Copy DLLs (suppress output)
copy lib\raylib.dll . >nul 2>&1

echo Starting game...
echo ===============================================
echo.

REM Run the game
astroboy4.exe

goto :end

:build_failed
echo.
echo ===============================================
echo BUILD FAILED!
echo ===============================================
echo Check the error messages above.
echo ===============================================
goto :end

:end
echo.
echo Game closed.
pause
