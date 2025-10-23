@echo off
REM Architect.AI Universal Launcher for Windows
REM This script launches the Python launcher which handles the rest

echo.
echo ============================================================
echo    🏗️ Architect.AI v2.0 - Production Dual-Mode System
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python not found in PATH
    echo    Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

REM Launch the Python launcher
python launch.py

if errorlevel 1 (
    echo.
    echo ❌ Application exited with an error
    pause
)

