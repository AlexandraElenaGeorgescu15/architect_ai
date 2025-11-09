# ============================================================
# Local AI Setup Script for Architect.AI
# ============================================================
# This script helps you set up local AI providers (Ollama + HuggingFace)

Write-Host "🚀 Architect.AI Local AI Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Ollama Installation
Write-Host "📋 Step 1: Checking Ollama Installation..." -ForegroundColor Yellow
try {
    $ollamaVersion = ollama --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Ollama is installed: $ollamaVersion" -ForegroundColor Green
    } else {
        throw "Ollama not found"
    }
} catch {
    Write-Host "❌ Ollama is NOT installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Ollama:" -ForegroundColor Yellow
    Write-Host "1. Go to: https://ollama.com/download" -ForegroundColor White
    Write-Host "2. Download for Windows" -ForegroundColor White
    Write-Host "3. Run the installer" -ForegroundColor White
    Write-Host "4. Restart your terminal" -ForegroundColor White
    Write-Host "5. Run this script again" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Step 2: Check if Ollama is running
Write-Host "📋 Step 2: Checking Ollama Server..." -ForegroundColor Yellow
$ollamaRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $ollamaRunning = $true
        Write-Host "✅ Ollama server is running" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Ollama server is NOT running" -ForegroundColor Yellow
    Write-Host "Starting Ollama server..." -ForegroundColor Cyan
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "✅ Ollama server started" -ForegroundColor Green
}

Write-Host ""

# Step 3: List available models
Write-Host "📋 Step 3: Checking Downloaded Models..." -ForegroundColor Yellow
$models = ollama list 2>$null
if ($models) {
    Write-Host $models -ForegroundColor White
} else {
    Write-Host "⚠️ No models downloaded yet" -ForegroundColor Yellow
}

Write-Host ""

# Step 4: Offer to download recommended models
Write-Host "📋 Step 4: Download Recommended Models?" -ForegroundColor Yellow
Write-Host ""
Write-Host "Recommended models for Architect.AI:" -ForegroundColor Cyan
Write-Host "  1. llama3.2:3b     - Fast, 2GB (RECOMMENDED for quick responses)" -ForegroundColor White
Write-Host "  2. codellama:7b    - Best for code generation, 4GB" -ForegroundColor White
Write-Host "  3. llama3.1:8b     - High quality, 4.7GB" -ForegroundColor White
Write-Host "  4. mistral:7b      - Good for diagrams, 4.1GB" -ForegroundColor White
Write-Host ""

$downloadChoice = Read-Host "Would you like to download models now? (Y/N)"

if ($downloadChoice -eq "Y" -or $downloadChoice -eq "y") {
    Write-Host ""
    Write-Host "Downloading llama3.2:3b (fast model)..." -ForegroundColor Cyan
    ollama pull llama3.2:3b
    
    Write-Host ""
    $downloadMore = Read-Host "Download codellama:7b for code generation? (Y/N)"
    if ($downloadMore -eq "Y" -or $downloadMore -eq "y") {
        Write-Host "Downloading codellama:7b..." -ForegroundColor Cyan
        ollama pull codellama:7b
    }
    
    Write-Host ""
    Write-Host "✅ Models downloaded successfully!" -ForegroundColor Green
} else {
    Write-Host "Skipping model downloads. You can download them later with:" -ForegroundColor Yellow
    Write-Host "  ollama pull llama3.2:3b" -ForegroundColor White
}

Write-Host ""

# Step 5: HuggingFace Token Setup
Write-Host "📋 Step 5: HuggingFace Token (Optional)" -ForegroundColor Yellow
Write-Host ""
Write-Host "HuggingFace token is only needed for:" -ForegroundColor Cyan
Write-Host "  - Downloading models for fine-tuning" -ForegroundColor White
Write-Host "  - Using the MermaidMistral specialized model" -ForegroundColor White
Write-Host ""
Write-Host "Current HF_TOKEN status: " -NoNewline
if ($env:HF_TOKEN) {
    Write-Host "✅ Set (token: $($env:HF_TOKEN.Substring(0, 8))...)" -ForegroundColor Green
} else {
    Write-Host "❌ Not set" -ForegroundColor Red
}

Write-Host ""
$setupHF = Read-Host "Would you like to set your HuggingFace token now? (Y/N)"

if ($setupHF -eq "Y" -or $setupHF -eq "y") {
    Write-Host ""
    Write-Host "To get your HuggingFace token:" -ForegroundColor Cyan
    Write-Host "1. Go to: https://huggingface.co/settings/tokens" -ForegroundColor White
    Write-Host "2. Click 'New token'" -ForegroundColor White
    Write-Host "3. Copy the token" -ForegroundColor White
    Write-Host ""
    
    $hfToken = Read-Host "Paste your HuggingFace token"
    
    if ($hfToken) {
        # Set for current session
        $env:HF_TOKEN = $hfToken
        
        # Set permanently (user-level)
        [System.Environment]::SetEnvironmentVariable("HF_TOKEN", $hfToken, "User")
        
        Write-Host "✅ HuggingFace token set successfully!" -ForegroundColor Green
        Write-Host "⚠️ You may need to restart your terminal for the token to take effect" -ForegroundColor Yellow
    }
} else {
    Write-Host "Skipping HuggingFace setup. You can set it later with:" -ForegroundColor Yellow
    Write-Host '  $env:HF_TOKEN = "your_token_here"' -ForegroundColor White
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "🎉 Local AI Setup Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run your Architect.AI application:" -ForegroundColor White
Write-Host "   python launch.py" -ForegroundColor White
Write-Host ""
Write-Host "2. In the app, select 'Ollama (Local)' as your provider" -ForegroundColor White
Write-Host ""
Write-Host "3. Choose a model from the dropdown" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"

