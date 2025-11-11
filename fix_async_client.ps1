# ============================================================================
# Fix AsyncClient 'proxies' Error
# ============================================================================
# This script upgrades groq and openai to versions compatible with httpx 0.28+

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Fixing AsyncClient 'proxies' Error" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "[WARNING] Virtual environment not activated!" -ForegroundColor Yellow
    Write-Host "Run: .venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit
    }
}

Write-Host "[1/4] Checking current versions..." -ForegroundColor Green
python -c "import groq; print(f'groq: {groq.__version__}')"
python -c "import openai; print(f'openai: {openai.__version__}')"
python -c "import httpx; print(f'httpx: {httpx.__version__}')"
Write-Host ""

Write-Host "[2/4] Uninstalling old versions..." -ForegroundColor Green
pip uninstall -y groq openai
Write-Host ""

Write-Host "[3/4] Installing latest compatible versions..." -ForegroundColor Green
pip install --no-cache-dir groq==0.33.0 openai==2.7.2
Write-Host ""

Write-Host "[4/4] Verifying installation..." -ForegroundColor Green
python -c "import groq; print(f'groq: {groq.__version__}')"
python -c "import openai; print(f'openai: {openai.__version__}')"
python -c "import httpx; print(f'httpx: {httpx.__version__}')"
Write-Host ""

Write-Host "============================================" -ForegroundColor Green
Write-Host "  Fix Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "The AsyncClient 'proxies' error should now be resolved." -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: You still have Gemini rate limits." -ForegroundColor Yellow
Write-Host "Cloud fallback will now use Groq (llama-3.3-70b) when local models fail." -ForegroundColor Yellow
