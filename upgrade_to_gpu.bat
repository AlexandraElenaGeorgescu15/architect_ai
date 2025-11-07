@echo off
echo ============================================================
echo   Upgrading PyTorch to GPU (CUDA) Version
echo ============================================================
echo.
echo You have: NVIDIA RTX 3500 Ada (12GB VRAM)
echo Current: PyTorch CPU-only (slow training)
echo Target:  PyTorch with CUDA (fast training)
echo.
echo This will:
echo   1. Uninstall CPU-only PyTorch
echo   2. Install CUDA-enabled PyTorch
echo   3. Enable GPU acceleration for fine-tuning
echo.
echo Estimated time: 2-5 minutes
echo.
pause

echo.
echo [Step 1/2] Uninstalling CPU-only PyTorch...
pip uninstall -y torch torchvision torchaudio

echo.
echo [Step 2/2] Installing CUDA-enabled PyTorch...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo.
echo ============================================================
echo   Testing GPU Installation
echo ============================================================
python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('GPU Name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

echo.
echo ============================================================
if errorlevel 1 (
    echo   Installation may have issues - check errors above
) else (
    echo   Installation Complete!
    echo.
    echo   Your GPU is now ready for fast fine-tuning!
    echo   Fine-tuning will be 10-100x faster than before.
)
echo ============================================================
echo.
pause
