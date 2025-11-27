# HuggingFace ↔ Ollama Compatibility Guide

## ⚠️ Important: They Are NOT Always Compatible

**Short Answer:** HuggingFace models are **NOT directly compatible** with Ollama. They require conversion, and conversion only works for specific formats.

## 🔄 How Conversion Works

### ✅ What Works (Automatic Conversion)

1. **GGUF Format Models** (Best Compatibility)
   - Pre-quantized models from TheBloke, QuantFactory, etc.
   - Formats: Q4_K_M, Q5_K_M, Q8_0, etc.
   - **Conversion Method:** `ollama import <model_name> <path_to_gguf>`
   - **Success Rate:** ~95%

2. **Ollama Hub Models**
   - Models already available on Ollama Hub
   - **Conversion Method:** `ollama pull <model_name>`
   - **Success Rate:** ~100% (if model exists)

### ❌ What Doesn't Work

1. **PyTorch Models (.bin, .safetensors)**
   - Raw HuggingFace models without GGUF conversion
   - **Why:** Ollama requires GGUF format
   - **Solution:** Need `llama.cpp` conversion pipeline (not implemented)

2. **Custom Architectures**
   - Models with non-standard architectures
   - **Why:** Ollama may not support the architecture
   - **Solution:** Use models known to work with Ollama

3. **Non-Quantized Models**
   - Full precision models (too large)
   - **Why:** Ollama works best with quantized models
   - **Solution:** Download quantized versions

## 📋 Current Implementation

### HuggingFace Service (`huggingface_service.py`)

The service tries **3 methods** in order:

```python
1. Try GGUF Import (ollama import)
   ↓ (if fails)
2. Try Modelfile Creation (ollama create -f Modelfile)
   ↓ (if fails)
3. Try Ollama Hub Pull (ollama pull)
   ↓ (if fails)
4. Return error: "Model needs GGUF format"
```

### Conversion Flow

```
HuggingFace Model Download
    ↓
Check for GGUF files
    ↓
[If GGUF found]
    → ollama import <name> <gguf_path>
    → Success! ✅
    ↓
[If GGUF not found]
    → Try ollama pull (check Ollama Hub)
    → Success! ✅
    ↓
[If both fail]
    → Error: "Model needs GGUF format" ❌
```

## 🎯 Fine-Tuning: Different System

**Important:** The fine-tuning system (`ollama_finetuning.py`) does **NOT** use HuggingFace models.

### Fine-Tuning Flow

```
1. User provides feedback/examples
    ↓
2. Create Modelfile with examples in system prompt
    ↓
3. Build Ollama model: ollama create <name> -f Modelfile
    ↓
4. Model is ready (no HuggingFace involved)
```

**Key Difference:**
- **HuggingFace fine-tuning:** Requires LoRA/QLoRA training (GPU, hours)
- **Ollama fine-tuning:** Uses Modelfile approach (CPU, seconds)

## 🔧 What Gets Registered Where

### Model Registry Structure

```json
{
  "ollama:model-name": {
    "provider": "ollama",
    "status": "available",
    "metadata": {
      "source": "huggingface",  // ← If converted from HF
      "huggingface_id": "codellama/CodeLlama-7b-Instruct-hf"
    }
  }
}
```

### Two Separate Systems

1. **HuggingFace → Ollama Conversion**
   - Downloads from HuggingFace Hub
   - Converts to Ollama format
   - Registers in ModelService
   - **Use Case:** Getting base models

2. **Ollama Fine-Tuning**
   - Uses existing Ollama models
   - Creates new models with Modelfile
   - Registers in ModelService
   - **Use Case:** Customizing models for specific tasks

## ⚠️ Common Issues & Solutions

### Issue 1: "Model needs GGUF format"

**Cause:** HuggingFace model doesn't have GGUF files

**Solutions:**
1. Search for GGUF version on HuggingFace (e.g., "TheBloke/ModelName-GGUF")
2. Use Ollama Hub directly: `ollama pull model-name`
3. Convert manually using `llama.cpp` (advanced)

### Issue 2: Conversion Fails Silently

**Cause:** GGUF file exists but `ollama import` fails

**Solutions:**
1. Check GGUF file size (should be > 100MB)
2. Verify Ollama is running: `ollama list`
3. Try manual import: `ollama import test-model path/to/file.gguf`
4. Check Ollama logs for errors

### Issue 3: Model Not Found in Ollama Hub

**Cause:** Model name doesn't match Ollama Hub naming

**Solutions:**
1. Check Ollama Hub: https://ollama.com/library
2. Use exact model name from Ollama Hub
3. Try common variations (e.g., "llama3" vs "llama3:8b")

## 📊 Compatibility Matrix

| Model Source | Format | Ollama Compatible? | Conversion Method |
|-------------|--------|-------------------|-------------------|
| HuggingFace | GGUF | ✅ Yes | `ollama import` |
| HuggingFace | PyTorch | ❌ No | Needs `llama.cpp` |
| HuggingFace | SafeTensors | ❌ No | Needs `llama.cpp` |
| Ollama Hub | Native | ✅ Yes | `ollama pull` |
| Local GGUF | GGUF | ✅ Yes | `ollama import` |
| Fine-tuned (Modelfile) | Ollama | ✅ Yes | `ollama create` |

## 🎯 Best Practices

### For Base Models:
1. **Prefer Ollama Hub** - Most reliable
   ```bash
   ollama pull llama3:8b
   ```

2. **If using HuggingFace** - Look for GGUF versions
   - Search: "model-name GGUF"
   - Popular sources: TheBloke, QuantFactory

3. **Avoid PyTorch models** - Unless you need full conversion pipeline

### For Fine-Tuning:
1. **Use Ollama Modelfile approach** - Fast, no GPU needed
2. **Don't mix with HuggingFace** - They're separate systems
3. **Fine-tune existing Ollama models** - Not HuggingFace models

## 🔍 How to Check Compatibility

### Before Downloading from HuggingFace:

```python
# Check if model has GGUF files
from huggingface_hub import HfApi
api = HfApi()
model_info = api.model_info("model-name")
gguf_files = [f for f in model_info.siblings if f.rfilename.endswith(".gguf")]

if gguf_files:
    print("✅ Compatible - Has GGUF files")
else:
    print("❌ Not compatible - No GGUF files found")
```

### After Conversion:

```bash
# Check if model is in Ollama
ollama list | grep model-name

# Test the model
ollama run model-name "test prompt"
```

## 📝 Summary

**Key Points:**
1. ✅ HuggingFace models **can** work with Ollama, but only if they have GGUF files
2. ✅ Conversion is automatic for GGUF models
3. ❌ PyTorch/SafeTensors models need manual conversion (not implemented)
4. ✅ Fine-tuning uses Ollama's Modelfile approach (separate from HuggingFace)
5. ✅ Best practice: Use Ollama Hub for base models, fine-tune with Modelfiles

**Current Status:**
- ✅ GGUF conversion: Working
- ✅ Ollama Hub pull: Working
- ❌ PyTorch conversion: Not implemented (would need `llama.cpp`)
- ✅ Fine-tuning: Working (uses Modelfile, not HuggingFace)

