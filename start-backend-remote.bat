@echo off
title Architect.AI Backend (Remote Access)
echo.
echo ============================================
echo   Architect.AI Backend Launcher
echo   For Remote Frontend Access
echo ============================================
echo.
echo Starting backend server...
echo.

:: Check if ngrok is installed
where ngrok >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] ngrok is not installed or not in PATH
    echo.
    echo To expose your backend to the internet, install ngrok:
    echo   1. Download from https://ngrok.com/download
    echo   2. Unzip and add to PATH
    echo   3. Run: ngrok config add-authtoken YOUR_TOKEN
    echo.
    echo Starting backend without ngrok...
    echo Your backend will only be accessible locally at http://localhost:8000
    echo.
    goto :start_backend
)

echo [INFO] ngrok detected!
echo.
echo Starting ngrok tunnel in background...
start /B ngrok http 8000 --log=stdout > ngrok.log 2>&1

:: Wait for ngrok to start
timeout /t 3 /nobreak >nul

:: Try to get ngrok URL
echo.
echo Fetching ngrok public URL...
curl -s http://localhost:4040/api/tunnels > ngrok_tunnels.json 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Could not fetch ngrok URL automatically
    echo Check ngrok dashboard at http://localhost:4040
) else (
    echo.
    echo ============================================
    echo   YOUR BACKEND URLs:
    echo ============================================
    echo.
    echo   Local:  http://localhost:8000
    echo.
    echo   To get your public ngrok URL:
    echo   Open http://localhost:4040 in your browser
    echo.
    echo ============================================
    echo.
    echo NEXT STEPS:
    echo   1. Open https://architect-ai-mvm.vercel.app/
    echo   2. Click the connection indicator (bottom-left)
    echo   3. Enter your ngrok URL (e.g., https://xxxx.ngrok.io)
    echo   4. Click "Save & Connect"
    echo ============================================
)
echo.

:start_backend
echo.
echo Starting FastAPI backend on port 8000...
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause
