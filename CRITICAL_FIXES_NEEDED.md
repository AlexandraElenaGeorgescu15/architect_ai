# Critical Fixes Needed - November 9, 2025

## Issues Identified

1. ❌ **Gemini API Key Not Working** - Even though provided: `AIzaSyAg6R0U0Noix5QRc4-mRio5ovaQz2CSSWs`
2. ❌ **Cloud Fallback Broken** - "All cloud providers failed"
3. ❌ **Generate Prototypes Not Working** - Button doesn't generate anything
4. ❌ **HTML Diagrams Not Generating** - Local models fail to generate HTML
5. ❌ **Diagram Quality Poor** - All using same model, not routing correctly
6. ❌ **Visual Editor Async Error** - `cannot access local variable 'asyncio'`
7. ❌ **Ollama Message Spam** - "Install Ollama" even though it's installed

## Status

✅ **Gemini API Key Saved** - Key has been stored in secrets manager

## Remaining Fixes Needed

### Fix 1: Verify Gemini API Key is Actually Used
**File:** `agents/universal_agent.py` line 744
**Issue:** Cloud fallback logic may not be using the saved key correctly

### Fix 2: Generate Prototypes Button
**Issue:** The "Generate Prototypes" button likely has the same batch mode issue as "Generate All Artifacts"
**Required:** Check `app_v2.py` for prototype generation logic

### Fix 3: HTML Diagram Generation
**Issue:** Local models are not generating proper HTML, falling back to static
**Files to check:**
- `components/mermaid_html_renderer.py`
- `agents/universal_agent.py` (HTML generation prompts)

### Fix 4: Model Routing
**Issue:** Not using Mistral for diagrams, using same model for everything
**File:** `components/artifact_router.py`

### Fix 5: Visual Editor Asyncio Error
**Issue:** Undefined asyncio variable
**Location:** Unknown - need to search for visual editor generation code

### Fix 6: Ollama Detection
**Issue:** Ollama check not working correctly
**File:** Search for "Install Ollama" message

## Quick Verification Commands

```bash
# 1. Verify Gemini key is saved
python -c "from config.api_key_manager import APIKeyManager; mgr = APIKeyManager(); key = mgr.get_key('gemini'); print('Key exists:',  bool(key))"

# 2. Test Gemini API directly
python -c "import google.generativeai as genai; genai.configure(api_key='AIzaSyAg6R0U0Noix5QRc4-mRio5ovaQz2CSSWs'); model = genai.GenerativeModel('gemini-pro'); print('Gemini works:', bool(model))"

# 3. Check Ollama is running
curl http://localhost:11434/api/tags

# 4. List available Ollama models
ollama list
```

## Priority Order

1. **CRITICAL:** Fix cloud fallback (Gemini) - blocks ERD generation
2. **HIGH:** Fix Generate Prototypes button
3. **HIGH:** Fix model routing (use Mistral for diagrams)
4. **MEDIUM:** Fix HTML diagram generation
5. **LOW:** Fix Ollama detection message
6. **LOW:** Fix visual editor asyncio error

## Notes for Next Session

The user has been patient but is frustrated. They need:
- Working diagram generation (either local with Mistral or cloud with Gemini)
- Working prototype generation
- Better quality outputs

The enhanced fine-tuning system we built is great, but the core app needs to work first!

