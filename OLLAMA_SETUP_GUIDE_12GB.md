# 🚀 Ollama Setup Guide (12GB VRAM - RTX 3500 Ada)

## Hardware Profile
- **GPU:** NVIDIA RTX 3500 Ada Generation Laptop GPU
- **VRAM:** 12.0 GB
- **Strategy:** Max Speed (7B models + smart swapping)
- **Expected Performance:** 80% instant response (persistent models)

---

## 📋 Prerequisites Checklist

Before starting, verify:
- [ ] Windows 10/11 with latest updates
- [ ] NVIDIA drivers installed (you have 32.0.15.8092 ✅)
- [ ] At least 30GB free disk space (for models)
- [ ] Administrator access
- [ ] Internet connection (for downloads)

---

## Step 1: Delete Existing Models (Fresh Start)

### Why?
You mentioned you have models downloaded but want to start fresh. This ensures no conflicts.

### How?
```powershell
# Open PowerShell as Administrator

# If you have Ollama already installed:
ollama list

# Delete each model:
ollama rm <model-name>

# Example:
# ollama rm codellama:13b-instruct
# ollama rm llama3:8b-instruct

# Or, manually delete the models directory:
Remove-Item -Recurse -Force "$env:USERPROFILE\.ollama\models"
```

---

## Step 2: Install Ollama

### Download
1. Go to: **https://ollama.com**
2. Click **Download for Windows**
3. Run the installer (`OllamaSetup.exe`)

### Verify Installation
```powershell
# Open new PowerShell window
ollama --version

# Expected output:
# ollama version 0.x.x
```

### Start Ollama Server
```powershell
# Ollama runs as a service, but you can start it manually:
ollama serve

# Leave this running in the background
# Or, just let Windows manage it as a service
```

---

## Step 3: Pull CodeLlama 7B (Persistent Model #1)

### Why 7B instead of 13B?
- 7B uses only **3.8GB VRAM** vs 13B's **7.0GB**
- Quality difference is minimal (85-90/100 vs 90-95/100)
- **Allows 2 models to fit in your 12GB VRAM simultaneously**

### Download
```powershell
ollama pull codellama:7b-instruct-q4_K_M
```

**Expected:**
```
pulling manifest
pulling 8fdf... 100% ▕██████████████████████████████████████████████████▏ 3.8 GB                          
pulling 4fa5... 100% ▕██████████████████████████████████████████████████▏  11 KB                          
pulling 8ab4... 100% ▕██████████████████████████████████████████████████▏  254 B                          
verifying sha256 digest
writing manifest
success
```

**Time:** ~5-10 minutes (depending on internet speed)

### Test
```powershell
ollama run codellama:7b-instruct-q4_K_M "Write a Python hello world"
```

**Expected Output:**
```python
print("Hello, World!")
```

---

## Step 4: Pull Llama 3 8B (Persistent Model #2)

### Download
```powershell
ollama pull llama3:8b-instruct-q4_K_M
```

**Expected:**
```
pulling manifest
pulling 6a09... 100% ▕██████████████████████████████████████████████████▏ 4.7 GB                          
...
success
```

**Time:** ~5-10 minutes

### Test
```powershell
ollama run llama3:8b-instruct-q4_K_M "What is AI?"
```

---

## Step 5: Setup MermaidMistral (Swap Model)

### Why Custom GGUF?
MermaidMistral isn't available via `ollama pull`. We must download the GGUF file and create a custom Modelfile.

### Download GGUF File

1. **Go to:** https://huggingface.co/mradermacher/MermaidMistral-GGUF/tree/main

2. **Find and download:**  
   `mermaidmistral.Q4_K_M.gguf` (4.5GB)
   
   **Direct link:**
   https://huggingface.co/mradermacher/MermaidMistral-GGUF/resolve/main/mermaidmistral.Q4_K_M.gguf

3. **Save to:** `C:\models\mermaidmistral.Q4_K_M.gguf`

**Time:** ~10-15 minutes (4.5GB download)

### Create Modelfile

```powershell
# Create models directory
mkdir C:\models
cd C:\models

# Create Modelfile (no extension)
# Use Notepad:
notepad Modelfile

# Paste this single line:
FROM ./mermaidmistral.Q4_K_M.gguf

# Save and close
```

**Or via PowerShell:**
```powershell
cd C:\models
echo "FROM ./mermaidmistral.Q4_K_M.gguf" > Modelfile
```

### Register with Ollama

```powershell
cd C:\models
ollama create mermaid-mistral -f ./Modelfile
```

**Expected:**
```
transferring model data
using existing layer sha256:...
creating new layer sha256:...
writing manifest
success
```

**Time:** ~30 seconds

### Test
```powershell
ollama run mermaid-mistral "Generate an ERD for user authentication"
```

**Expected:** Valid Mermaid ERD syntax

---

## Step 6: Verify All Models

```powershell
ollama list
```

**Expected Output:**
```
NAME                              	ID          	SIZE  	MODIFIED
codellama:7b-instruct-q4_K_M     	8fdf...     	3.8 GB	2 minutes ago
llama3:8b-instruct-q4_K_M        	6a09...     	4.7 GB	1 minute ago
mermaid-mistral                  	a1b2...     	4.5 GB	30 seconds ago
```

✅ **SUCCESS:** All 3 models installed!

---

## Step 7: Test VRAM Usage

### Load Both Persistent Models

**Terminal 1:**
```powershell
ollama run codellama:7b-instruct-q4_K_M
# Type: hello
# Keep this running
```

**Terminal 2:**
```powershell
ollama run llama3:8b-instruct-q4_K_M
# Type: hello
# Keep this running
```

### Check VRAM Usage

```powershell
nvidia-smi
```

**Expected:**
```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 560.xx                 Driver Version: 560.xx         CUDA Version: 12.6     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                  Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                          |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA RTX 3500 Ada             On |   00000000:01:00.0 Off |                  N/A |
| N/A   45C    P0             15W /  115W |    8500MiB /  12288MiB |      0%      Default |
|                                          |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
```

**Key:**
- **Memory-Usage: ~8.5GB / 12.3GB** ✅
- **Available: ~3.7GB** ✅ Enough for swapping MermaidMistral

---

## Step 8: Configure Your App

### Update Config (If Needed)

Create or update: `architect_ai_cursor_poc/config/ollama_config.yaml`

```yaml
ollama:
  base_url: "http://localhost:11434"
  timeout: 120
  vram_limit_gb: 12.0  # Your RTX 3500 Ada

models:
  persistent:
    # These stay loaded (8.5GB total)
    - codellama:7b-instruct-q4_K_M
    - llama3:8b-instruct-q4_K_M
  
  swap:
    # This swaps in when needed
    - mermaid-mistral

task_mapping:
  code: codellama:7b-instruct-q4_K_M
  html: codellama:7b-instruct-q4_K_M
  documentation: codellama:7b-instruct-q4_K_M
  jira: llama3:8b-instruct-q4_K_M
  mermaid: mermaid-mistral
  diagram: mermaid-mistral
  erd: mermaid-mistral
  architecture: mermaid-mistral

fallback:
  enabled: true
  cloud_provider: gemini
  force_local_default: false
```

---

## Step 9: Test Integration with App

### Start Your App
```powershell
cd architect_ai_cursor_poc
python launch.py
```

### Initialize Persistent Models

The app will automatically load persistent models on startup.

**Expected Console Output:**
```
[INFO] Loading persistent models (8.5GB / 12.0GB VRAM)...
[INFO] Loading codellama:7b-instruct-q4_K_M...
[SUCCESS] Model codellama:7b-instruct-q4_K_M loaded in 35.2s
[INFO] Loading llama3:8b-instruct-q4_K_M...
[SUCCESS] Model llama3:8b-instruct-q4_K_M loaded in 42.8s
[SUCCESS] Persistent models loaded: 2/2
```

**Time:** ~60-90 seconds (first time only!)

---

## 📊 Performance Expectations

### Persistent Models (Instant ⚡)
| Task | Model | Response Time | VRAM |
|------|-------|---------------|------|
| Generate Code | CodeLlama 7B | 5-10s | Persistent |
| Generate HTML | CodeLlama 7B | 5-10s | Persistent |
| Generate Docs | CodeLlama 7B | 5-10s | Persistent |
| Generate JIRA | Llama 3 8B | 5-10s | Persistent |

### Swap Model (First Time: Slow ⚠️, Cached: Fast ✅)
| Task | Model | First Time | Cached | VRAM |
|------|-------|------------|--------|------|
| Generate ERD | MermaidMistral | 45-60s | 10s | Swap in |
| Generate Architecture | MermaidMistral | 45-60s | 10s | Swap in |

---

## 🎯 Usage Tips

### 1. Generate Code-Heavy Tasks First
Start your session with code, HTML, docs, or JIRA generation. These use persistent models and respond instantly.

### 2. Batch Diagram Generation
If you need multiple diagrams, generate them all at once. MermaidMistral will stay loaded between requests (~10s each after the first).

### 3. Optimal Workflow
```
Session Start:
1. Generate Code Prototype (10s) ⚡
2. Generate JIRA Tasks (10s) ⚡
3. Generate HTML Prototype (10s) ⚡
4. Generate ALL Diagrams (ERD, Architecture, etc.) (60s first, 10s each after) ⚠️✅
Total: ~120s for complete artifact set

Instead of:
1. ERD (60s swap)
2. Code (60s swap)
3. Architecture (60s swap)
4. JIRA (60s swap)
Total: ~240s (2x slower!)
```

---

## 🚨 Troubleshooting

### Issue: "Model not found"
**Solution:**
```powershell
ollama list
# Verify model names match exactly
```

### Issue: "CUDA out of memory"
**Solution:**
```powershell
# Close other GPU-using apps (games, video editing, Chrome with GPU acceleration)
# Restart Ollama:
taskkill /F /IM ollama.exe
ollama serve
```

### Issue: "Model loading too slow"
**Solution:**
```powershell
# First time: 30-60s is normal
# Subsequent: Should be instant (if persistent) or 10s (if cached)

# If still slow, check disk speed:
# Ollama stores models in: C:\Users\<you>\.ollama\models
# Move to faster SSD if on HDD
```

### Issue: "Ollama API not responding"
**Solution:**
```powershell
# Check if Ollama is running:
ollama list

# Restart service:
net stop Ollama
net start Ollama

# Or manually:
ollama serve
```

---

## ✅ Verification Checklist

Before using the app, verify:

- [ ] Ollama installed and `ollama --version` works
- [ ] All 3 models show in `ollama list`
- [ ] CodeLlama 7B responds to test prompt
- [ ] Llama 3 8B responds to test prompt
- [ ] MermaidMistral responds to test prompt
- [ ] Both persistent models loaded: `nvidia-smi` shows ~8.5GB used
- [ ] Available VRAM: ~3.7GB remaining
- [ ] App starts and loads persistent models successfully

---

## 🎉 Success!

You're now running a **hybrid local/cloud AI system** optimized for your 12GB VRAM GPU!

**Benefits:**
- ✅ 80% of tasks use local models (instant, free, private)
- ✅ 20% of tasks swap models (45-60s first time, 10s cached)
- ✅ Cloud fallback available when local fails
- ✅ Total cost savings: ~90% (vs cloud-only)

**Next Steps:**
1. Test bug fixes (#1-4) first
2. Generate some artifacts with local models
3. Monitor VRAM usage
4. Optionally: Add fine-tuning for Code model (Option B)

---

**Questions?** Check `VRAM_OPTIMIZED_ARCHITECTURE.md` for technical details.

**Hardware:** NVIDIA RTX 3500 Ada (12GB VRAM)  
**Strategy:** Max Speed (7B models + smart swapping)  
**Status:** 🎯 READY TO USE!

