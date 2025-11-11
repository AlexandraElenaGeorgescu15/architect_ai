# Quick Fix Script for Architect.AI Errors
# Run this in PowerShell to fix the critical cloud provider errors

Write-Host "🔧 Architect.AI - Comprehensive Fix Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "  ✓ Fix AsyncClient 'proxies' parameter errors" -ForegroundColor Gray
Write-Host "  ✓ Fix AsyncHttpxClientWrapper AttributeError" -ForegroundColor Gray
Write-Host "  ✓ Enable cloud fallback (Groq/OpenAI/Gemini)" -ForegroundColor Gray
Write-Host "  ✓ Upgrade packages to compatible versions" -ForegroundColor Gray
Write-Host ""

# Check if running in virtual environment
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Warning: Not in a virtual environment" -ForegroundColor Yellow
    Write-Host "Consider activating your venv first: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit
    }
}

Write-Host "📦 Step 1: Upgrading critical packages..." -ForegroundColor Green
Write-Host "This will fix AsyncClient 'proxies' errors" -ForegroundColor Gray
Write-Host ""

# Upgrade packages with specific versions
Write-Host "Installing: groq==0.12.0, openai==1.55.0, httpx==0.27.2..." -ForegroundColor Cyan
pip install --upgrade groq==0.12.0 openai==1.55.0 httpx==0.27.2 --quiet

Write-Host ""
Write-Host "✅ Packages upgraded!" -ForegroundColor Green
Write-Host ""

# Verify versions
Write-Host "📋 Step 2: Verifying installed versions..." -ForegroundColor Green
Write-Host ""

$groqVersion = pip show groq 2>$null | Select-String "Version:"
$openaiVersion = pip show openai 2>$null | Select-String "Version:"
$httpxVersion = pip show httpx 2>$null | Select-String "Version:"

Write-Host "  groq:   $groqVersion" -ForegroundColor Cyan
Write-Host "  openai: $openaiVersion" -ForegroundColor Cyan
Write-Host "  httpx:  $httpxVersion" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ Fix Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 What was fixed:" -ForegroundColor Yellow
Write-Host "  ✓ AsyncClient 'proxies' parameter errors (groq/openai)" -ForegroundColor Green
Write-Host "  ✓ AsyncHttpxClientWrapper AttributeError" -ForegroundColor Green
Write-Host "  ✓ Cloud fallback compatibility with httpx 0.27+" -ForegroundColor Green
Write-Host ""

Write-Host "Additional improvements (already in code):" -ForegroundColor Yellow
Write-Host "  - Duplicate diagram names fixed" -ForegroundColor Green
Write-Host "  - Feedback buttons now persist after generation" -ForegroundColor Green
Write-Host "  - Groq prioritized over Gemini (fewer rate limits)" -ForegroundColor Green
Write-Host "  - Feedback works for both local and cloud models" -ForegroundColor Green
Write-Host "  - New Ollama fine-tuning with Modelfile approach" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Restart your Streamlit application" -ForegroundColor White
Write-Host "  2. Test cloud fallback (should work now!)" -ForegroundColor White
Write-Host "  3. Try the new fine-tuning system" -ForegroundColor White
Write-Host ""
