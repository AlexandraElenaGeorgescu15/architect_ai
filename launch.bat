@echo off
REM Architect.AI FastAPI + React Launcher for Windows
REM Launches both backend (FastAPI) and frontend (React) servers

echo.
echo ============================================================
echo    Architect.AI v3.5.2 - FastAPI + React Edition
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo    Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found in PATH
    echo    Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

echo Python and Node.js found
echo.

REM Check if backend dependencies are installed
echo Checking backend dependencies...
python -c "import fastapi, slowapi" >nul 2>&1
if errorlevel 1 (
    echo Installing backend dependencies...
    echo This may take a few minutes...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install backend dependencies
        echo Please run INSTALL_DEPENDENCIES.bat manually
        pause
        exit /b 1
    )
    echo Backend dependencies installed successfully
)

REM Check if frontend dependencies are installed
echo Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
    cd ..
)

echo.
echo ============================================================
echo    Starting Architect.AI...
echo ============================================================
echo.
echo Backend API:  http://localhost:8000
echo Frontend App: http://localhost:3000
echo API Docs:     http://localhost:8000/api/docs
echo.
echo Press Ctrl+C to stop both servers
echo.

REM Start backend in a new window
start "Architect.AI Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
start "Architect.AI Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo Both servers are starting...
echo    Backend and Frontend windows have been opened
echo.
echo    Close the windows or press Ctrl+C in each to stop
echo.

pause
