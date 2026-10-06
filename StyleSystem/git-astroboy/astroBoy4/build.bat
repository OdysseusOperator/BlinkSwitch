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
echo Output: astroboy4.exe
echo Size: 
dir astroboy4.exe | findstr astroboy4.exe
echo.
echo === NEW FEATURES from astroBoy3 ===
echo - Procedural audio system (shoot, explosion, thruster sounds)
echo - Thruster flame animation with randomized effects
echo - Advanced asteroid spawning with edge-based spawning and cooldowns
echo - Asteroids split into smaller pieces when destroyed
echo - Minimap/Radar system in bottom-right corner
echo - Mothership station with docking detection at position 200,200
echo - Camera-follow system - ship stays centered
echo - Core constants and types system (centralized configuration)
echo.
echo === CORE FEATURES ===
echo - Clay UI integration
echo - 3D rotating asteroids with 4 different shapes
echo - Modular gameobjects and systems architecture
echo - Physics-based gameplay with momentum
echo - Menu and Game Over screens
echo.

REM Copy DLLs (suppress output)
copy lib\raylib.dll . >nul 2>&1

echo Run with: astroboy4.exe
echo ===============================================
goto :end

:build_failed
echo.
echo ===============================================
echo BUILD FAILED!
echo ===============================================
echo Check the error messages above.
echo ===============================================

:end
echo.
pause
