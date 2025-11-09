# 🔧 Troubleshooting Guide - Architect.AI

Common issues and their solutions.

---

## Installation Issues

### Python Version Errors

**Error:** `SyntaxError` or `ImportError` with type hints

**Cause:** Python version < 3.9

**Solution:**
```bash
# Check version
python --version

# Must be Python 3.9 or higher
# Upgrade Python: https://www.python.org/downloads/
```

---

### Dependency Installation Failures

**Error:** `pip install` fails with compilation errors

**Solution:**
```bash
# Update pip first
python -m pip install --upgrade pip

# Try installing with pre-built wheels
pip install --only-binary :all: -r requirements.txt

# If specific package fails (e.g., chromadb)
pip install chromadb --no-build-isolation
```

**Alternative:** Use virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Ollama Issues

### "Ollama not running" / Connection Refused

**Error:** `ConnectionError: Failed to connect to http://localhost:11434`

**Solutions:**

**1. Start Ollama service:**
```bash
# Option A: Run in terminal
ollama serve

# Option B (Windows): Check if already running
tasklist | findstr ollama

# Option C (Linux/Mac): Check process
ps aux | grep ollama
```

**2. Verify Ollama is accessible:**
```bash
curl http://localhost:11434/api/tags
```

**3. Check firewall:**
- Allow connections to `localhost:11434`
- Disable antivirus temporarily to test

---

### "No models downloaded"

**Error:** Ollama running but no models available

**Solution:**
```bash
# List available models
ollama list

# Download a model (recommended)
ollama pull llama3.2:3b         # 2GB, fast
# OR
ollama pull codellama:7b-instruct  # 4GB, code-focused
# OR
ollama pull llama3:8b           # 5GB, higher quality
```

---

### Ollama slow or hanging

**Cause:** Model too large for your system RAM/VRAM

**Solutions:**

**1. Use smaller model:**
```bash
ollama pull llama3.2:3b  # Only 2GB
```

**2. Check system resources:**
- **RAM:** Need at least 8GB free
- **VRAM (GPU):** Ollama uses GPU if available
- Close other applications

**3. Set concurrency limit:**
```bash
# Edit .env
OLLAMA_MAX_LOADED_MODELS=1
```

---

## API Key Issues

### "No API key configured"

**Error:** App shows "Configure API keys" warning

**Solution:**

**1. Create `.env` file** in `architect_ai_cursor_poc/` directory:
```bash
# Copy template
cp .env.example .env

# Edit with your keys
nano .env  # or use any text editor
```

**2. Add API key** (choose one provider):
```bash
GROQ_API_KEY=gsk_your_key_here
```

**3. Restart the app**

---

### "Invalid API key" / Authentication Failed

**Error:** `401 Unauthorized` or `Invalid API key`

**Causes & Solutions:**

**1. Wrong key format:**
- Groq keys start with `gsk_`
- OpenAI keys start with `sk-`
- Gemini keys start with `AIza`

**2. Key expired or deactivated:**
- Generate new key from provider dashboard

**3. Key not loaded:**
```bash
# Check if .env file exists
ls -la .env

# Verify key is set (don't print actual key!)
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Key set:', bool(os.getenv('GROQ_API_KEY')))"
```

**4. Restart required:**
- Stop app (Ctrl+C)
- Run `streamlit cache clear`
- Restart: `python launch.py`

---

### "Rate limit exceeded"

**Error:** `429 Too Many Requests`

**Solutions:**

**1. Wait and retry:**
- Free tiers have rate limits
- Wait 1-5 minutes

**2. Use different provider:**
- Switch from OpenAI to Groq (higher limits)
- Use Ollama (no limits, local)

**3. Reduce concurrency:**
```python
# In app, disable "Generate All Artifacts"
# Generate one artifact at a time
```

---

## RAG / ChromaDB Issues

### "ChromaDB connection failed"

**Error:** `Failed to initialize ChromaDB`

**Solutions:**

**1. Reset ChromaDB:**
```bash
# Delete and recreate index
rm -rf rag/index/
python -m rag.ingest
```

**2. Check permissions:**
```bash
# Ensure directory is writable
chmod -R 755 rag/index/
```

**3. Disable telemetry** (may cause issues):
```python
# Already done in app, but verify .env has:
ANONYMIZED_TELEMETRY=False
CHROMA_TELEMETRY=False
```

---

### "No RAG results" / Empty Context

**Error:** RAG retrieval returns 0 chunks

**Causes & Solutions:**

**1. No code indexed:**
```bash
# Check if index exists
ls -la rag/index/

# If empty, run manual indexing
python -m rag.ingest
```

**2. Code in wrong location:**
- Your project must be in a **sibling directory** to `architect_ai_cursor_poc/`
- **Correct:**
  ```
  parent-folder/
  ├── architect_ai_cursor_poc/  ← Tool
  └── your-project/             ← Your code
  ```
- **Incorrect:**
  ```
  architect_ai_cursor_poc/
  └── your-project/  ← Tool excludes its own subdirectories!
  ```

**3. File types not supported:**
- Supported: `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.cs`, `.java`
- Check `rag/config.yaml` for `allow_extensions`

**4. Files excluded by filters:**
```yaml
# Check rag/config.yaml ignore_globs
# Common exclusions:
- "node_modules/**"
- "dist/**"
- ".git/**"
```

---

### ChromaDB version conflict

**Error:** `AttributeError: module 'chromadb' has no attribute 'Client'`

**Solution:**
```bash
# Reinstall ChromaDB
pip uninstall chromadb -y
pip install chromadb==0.4.22

# Or latest
pip install --upgrade chromadb
```

---

## Artifact Generation Issues

### "Meeting notes too short"

**Error:** Warning shown in UI

**Cause:** Input < 80 characters

**Solution:**
Add more detail:
```
❌ BAD: "Add user login"

✅ GOOD: "Create a user authentication system with email/password login, 
registration form, password reset via email, JWT token management, and 
session handling. Integrate with existing UserService."
```

---

### "Mermaid syntax error" / Invalid Diagram

**Error:** Generated diagram has validation errors

**Cause:** AI generated invalid Mermaid syntax

**Solution:**

**1. Automatic retry** (happens by default):
- System retries up to 2 times
- Uses syntax corrector

**2. Manual retry:**
- Click "Generate ERD" again
- Try different AI provider (Groq is more reliable for diagrams)

**3. Enable Enhanced RAG:**
- Provides more context to AI
- Checkbox in Artifact Generation section

---

### Artifacts take too long to generate

**Issue:** 30+ seconds per artifact

**Causes & Solutions:**

**1. Slow AI provider:**
- **OpenAI GPT-4:** 10-30 seconds (high quality but slow)
- **Switch to Groq:** 0.5-2 seconds (fast, free tier)
- **Use Ollama:** 3-10 seconds (local, no network delay)

**2. Too much RAG context:**
- Disable "Enhanced RAG" (uses 18 chunks instead of 100)
- Reduces context size = faster generation

**3. Large codebase:**
- RAG retrieval slower with 10,000+ files
- Consider indexing only relevant directories

---

### "Quality score too low" / Validation Failed

**Error:** Artifact score < 60/100

**Causes:**

**1. Poor AI output:**
- Model generated incomplete/incorrect content

**Solutions:**
- **Automatic:** System retries 2x with better prompts
- **Manual:** Add more detail to meeting notes
- **Switch model:** Try GPT-4 instead of Ollama

**2. Validation too strict:**
- Current threshold: 60/100
- Can be adjusted in `validation/output_validator.py`

---

## Fine-Tuning Issues

### "Training dataset empty"

**Error:** Cannot start fine-tuning, dataset has 0 examples

**Cause:** No feedback collected yet

**Solution:**
1. Generate some artifacts
2. Go to "🎓 Fine-Tuning" tab
3. Add feedback entries (artifact type, original output, corrected version)
4. System needs minimum 50 examples for automatic trigger

---

### "GPU not available" during training

**Warning:** Training will use CPU (slow)

**Solutions:**

**1. Verify GPU:**
```python
import torch
print(torch.cuda.is_available())  # Should be True
print(torch.cuda.get_device_name(0))
```

**2. Install CUDA toolkit:**
- NVIDIA GPU required
- Download: https://developer.nvidia.com/cuda-downloads

**3. Install PyTorch with CUDA:**
```bash
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

**4. Use smaller batch size:**
- Reduce from 4 to 2 or 1
- Settings in Fine-Tuning UI

---

### Training crashes / Out of Memory

**Error:** `CUDA out of memory` or `RuntimeError: CUDA error`

**Solutions:**

**1. Reduce batch size:**
- Change from 4 → 2 → 1

**2. Reduce LoRA rank:**
- Change from 16 → 8

**3. Use QLoRA instead of LoRA:**
- Enable 4-bit quantization (checkbox in UI)

**4. Use CPU training:**
- Slower but won't crash
- Automatically falls back if GPU unavailable

**5. Close other GPU applications:**
```bash
# Check GPU usage
nvidia-smi

# Kill GPU processes if needed
```

---

## File System / Permission Issues

### "Permission denied" errors

**Error:** Cannot write to `outputs/` or `rag/index/`

**Solutions:**

**1. Check directory permissions:**
```bash
# Make writable
chmod -R 755 architect_ai_cursor_poc/outputs/
chmod -R 755 architect_ai_cursor_poc/rag/index/
```

**2. Run without admin:**
- Don't run with sudo/admin unless necessary

**3. Antivirus blocking:**
- Add `architect_ai_cursor_poc/` to antivirus exceptions

---

### "File not found" errors

**Error:** `FileNotFoundError: meeting_notes.md`

**Solution:**

**1. Create inputs directory:**
```bash
mkdir -p inputs/
```

**2. Add meeting notes file:**
```bash
echo "Your feature requirements here" > inputs/meeting_notes.md
```

**3. Or upload via UI:**
- Go to "📝 Meeting Notes" section
- Enter text directly

---

## UI / Streamlit Issues

### App won't start / Import errors

**Error:** `ModuleNotFoundError` when running `streamlit run`

**Solutions:**

**1. Install dependencies:**
```bash
pip install -r requirements.txt
```

**2. Check Python path:**
```bash
# Ensure you're in correct directory
cd architect_ai_cursor_poc/
python launch.py
```

**3. Use launcher script:**
```bash
python launch.py  # Instead of streamlit run directly
```

---

### UI frozen / Not responding

**Issue:** App hangs during generation

**Causes & Solutions:**

**1. Long-running operation:**
- "Generate All Artifacts" takes 2-5 minutes
- Be patient, check console for progress

**2. Browser timeout:**
- Refresh page
- Check terminal for errors

**3. Streamlit cache issue:**
```bash
streamlit cache clear
python launch.py
```

---

### Unicode/Emoji display issues (Windows)

**Error:** `'charmap' codec can't encode character`

**Solution:**
- Already fixed in v3.5.1+
- If still occurring, set console to UTF-8:
```bash
chcp 65001  # Windows
```

---

## Performance Issues

### Slow indexing (RAG ingestion)

**Issue:** `python -m rag.ingest` takes 10+ minutes

**Causes:**

**1. Large codebase:**
- 10,000+ files = slow indexing

**Solutions:**
- Add exclusions to `rag/config.yaml`:
  ```yaml
  ignore_globs:
    - "tests/**"      # Exclude tests if not needed
    - "docs/**"       # Exclude documentation
    - "**/vendor/**"  # Exclude dependencies
  ```

**2. No GPU for embeddings:**
- Install PyTorch with CUDA (see above)

---

### High memory usage

**Issue:** App uses 4-8GB RAM

**Causes:**
- Knowledge Graph caching
- ChromaDB in-memory
- Multiple AI models loaded

**Solutions:**

**1. Reduce max chunks:**
```python
# In app, disable Enhanced RAG
# Uses 18 chunks instead of 100
```

**2. Restart app periodically:**
- Clears caches

**3. Use smaller Ollama models:**
```bash
ollama pull llama3.2:3b  # Instead of 8b
```

---

## Getting More Help

### Check Logs

**1. App logs:**
```bash
# Terminal shows real-time logs
# Look for [ERROR] or [WARN] messages
```

**2. ChromaDB logs:**
```bash
# Check rag/index/chroma.log
tail -f rag/index/chroma.log
```

### Run Diagnostic Script

```bash
python tests/check_setup.py
```

This checks:
- Python version
- Dependencies installed
- Ollama running
- Project structure
- API keys configured

### Report a Bug

If issue persists:

1. **Run verification:**
   ```bash
   python tests/run_tests.py > test_results.txt
   ```

2. **Collect info:**
   - Python version: `python --version`
   - OS: Windows/Linux/Mac + version
   - Error message (full traceback)

3. **Submit GitHub issue** with collected info

---

## Still Need Help?

- **GitHub Issues:** Report bugs with detailed description
- **Documentation:** Read `README.md` and `TECHNICAL_DOCUMENTATION.md`
- **Tests:** Run full test suite to identify specific failures

---

**Most issues are configuration-related and easily fixed. Don't give up!** 🛠️

