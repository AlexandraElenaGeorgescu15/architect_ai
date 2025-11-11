# Quick Package Fix for Architect.AI
# Fixes AsyncClient errors with cloud providers

Write-Host "Architect.AI - Package Fix Script" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check virtual environment
if (-not $env:VIRTUAL_ENV) {
    Write-Host "WARNING: Not in a virtual environment" -ForegroundColor Yellow
    Write-Host "Consider activating your venv first" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit
    }
}

Write-Host "Upgrading packages..." -ForegroundColor Green
Write-Host ""

# Upgrade critical packages
pip install --upgrade groq==0.12.0 openai==1.55.0 httpx==0.27.2

Write-Host ""
Write-Host "Package upgrade complete!" -ForegroundColor Green
Write-Host ""

# Verify versions
Write-Host "Installed versions:" -ForegroundColor Cyan
pip show groq openai httpx | Select-String "Name:|Version:"

Write-Host ""
Write-Host "Next step: Restart your Streamlit app" -ForegroundColor Yellow
Write-Host ""
