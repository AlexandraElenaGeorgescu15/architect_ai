<#
.SYNOPSIS
    Test ngrok connection and open browser to accept warning
.DESCRIPTION
    Opens the ngrok URL in browser to accept the warning page, then tests the connection
#>

param(
    [string]$NgrokUrl = "https://verdell-tricky-verena.ngrok-free.dev"
)

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Testing Ngrok Connection" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Opening ngrok URL in browser..." -ForegroundColor Yellow
Write-Host "  URL: $NgrokUrl" -ForegroundColor White
Write-Host "  Please click 'Visit Site' on the warning page" -ForegroundColor Yellow
Write-Host ""

# Open browser
Start-Process $NgrokUrl

Write-Host "Waiting 5 seconds for you to accept the warning..." -ForegroundColor Gray
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Step 2: Testing API connection..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "$NgrokUrl/api/health" -Headers @{
        'ngrok-skip-browser-warning' = 'true'
    } -UseBasicParsing -ErrorAction Stop
    
    Write-Host "✅ SUCCESS! Connection works!" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor White
    Write-Host "   Response: $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Connection failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Make sure you clicked 'Visit Site' on the ngrok warning page" -ForegroundColor White
    Write-Host "  2. Check that the backend is running" -ForegroundColor White
    Write-Host "  3. Verify the ngrok URL is correct" -ForegroundColor White
}

Write-Host ""
