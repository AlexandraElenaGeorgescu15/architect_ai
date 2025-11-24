@echo off
REM Quick dependency installer for Architect.AI
REM Run this if you get "ModuleNotFoundError" errors

echo.
echo ============================================================
echo    Installing Architect.AI Dependencies
echo ============================================================
echo.

cd /d "%~dp0"

echo Installing backend dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install backend dependencies
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo ============================================================
echo    Dependencies Installed Successfully!
echo ============================================================
echo.
echo You can now run launch.bat to start the application
echo.
pause

