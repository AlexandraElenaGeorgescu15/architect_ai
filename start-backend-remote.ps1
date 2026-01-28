<#
.SYNOPSIS
    Architect.AI Backend Launcher for Remote Access
.DESCRIPTION
    Starts the FastAPI backend and optionally exposes it via ngrok
    so your deployed frontend at https://architect-ai-mvm.vercel.app can connect.
#>

$Host.UI.RawUI.WindowTitle = "Architect.AI Backend (Remote Access)"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Architect.AI Backend Launcher" -ForegroundColor Cyan
Write-Host "  For Remote Frontend Access" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check if ngrok is available
$ngrokInstalled = Get-Command ngrok -ErrorAction SilentlyContinue

if (-not $ngrokInstalled) {
    Write-Host "[WARNING] ngrok is not installed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To expose your backend to the internet:" -ForegroundColor White
    Write-Host "  1. Download ngrok from https://ngrok.com/download" -ForegroundColor Gray
    Write-Host "  2. Extract and add to PATH" -ForegroundColor Gray
    Write-Host "  3. Run: ngrok config add-authtoken YOUR_TOKEN" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Starting backend locally only..." -ForegroundColor Yellow
    Write-Host "Backend URL: http://localhost:8000" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[OK] ngrok detected!" -ForegroundColor Green
    Write-Host ""
    
    # Start ngrok (HTTP 8000)
    Write-Host "Starting ngrok tunnel..." -ForegroundColor Cyan
    $ngrokProcess = Start-Process -FilePath "ngrok" -ArgumentList "http","http://127.0.0.1:8000","--log=stdout" -RedirectStandardOutput "ngrok.log" -RedirectStandardError "ngrok.err" -PassThru -NoNewWindow
    
    # Wait for ngrok to initialize
    Start-Sleep -Seconds 3
    
    # Try to get the public URL
    try {
        $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        $publicUrl = ($tunnels.tunnels | Where-Object { $_.proto -eq "https" }).public_url
        
        if ($publicUrl) {
            Write-Host ""
            Write-Host "============================================" -ForegroundColor Green
            Write-Host "  YOUR BACKEND URLs:" -ForegroundColor Green
            Write-Host "============================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "  Local:   http://localhost:8000" -ForegroundColor White
            Write-Host "  Public:  $publicUrl" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "============================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "NEXT STEPS:" -ForegroundColor Cyan
            Write-Host "  1. Open https://architect-ai-mvm.vercel.app/" -ForegroundColor White
            Write-Host "  2. Click the connection indicator (bottom-left)" -ForegroundColor White
            Write-Host "  3. Enter: $publicUrl" -ForegroundColor Yellow
            Write-Host "  4. Click 'Save & Connect'" -ForegroundColor White
            Write-Host ""
            
            # Copy to clipboard
            $publicUrl | Set-Clipboard
            Write-Host "[INFO] Public URL copied to clipboard!" -ForegroundColor Green
            Write-Host ""
        }
    } catch {
        Write-Host "[WARNING] Could not fetch ngrok URL automatically" -ForegroundColor Yellow
        Write-Host "Check ngrok dashboard at http://localhost:4040" -ForegroundColor Gray
    }
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Starting FastAPI backend on port 8000..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Start the backend
try {
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
} finally {
    # Cleanup ngrok when backend stops
    if ($ngrokProcess) {
        Write-Host ""
        Write-Host "Stopping ngrok..." -ForegroundColor Yellow
        Stop-Process -Id $ngrokProcess.Id -ErrorAction SilentlyContinue
    }
}
