# 🔬 Comprehensive System Diagnosis

**Date:** November 10, 2025
**Purpose:** Verify all critical systems are working correctly

---

## 📊 What Should Be Happening

### Flow for Artifact Generation:

```
1. User clicks "Generate ERD"
2. app_v2.py retrieves RAG context (lines 240-278)
   ├─ Enhanced RAG: agent.enhanced_rag_context = enhanced_context
   └─ Standard RAG: agent.rag_context = retrieved_context
3. Agent calls smart_generator.generate() (line 715-730)
   ├─ Passes: meeting_notes, rag_context, feature_requirements
   └─ smart_generator._build_context_prompt() combines all context
4. smart_generator tries local models (lines 564-663)
   ├─ Uses full_context_prompt (has RAG + meeting notes)
   └─ Validates quality
5. If local fails, cloud fallback (lines 719-800)
   ├─ Calls cloud_fallback_fn with full context
   └─ Saves to finetune_datasets/cloud_responses/
6. Returns result to user
```

---

## 🔍 Diagnostic Checks

### Check 1: Is RAG Context Being Retrieved?

**Expected logs:**
```
[HH:MM:SS] 🧠 Intelligent RAG: 18 chunks, 3000 tokens (ollama local: 18 chunks for fast 8K context)
[HH:MM:SS] 📚 Standard RAG: 18 chunks from Ollama (Local)
```

**If missing:**
- RAG retrieval failed
- Check: `agent.rag_context` is empty
- Check: ChromaDB connection

### Check 2: Is Context Reaching Smart Generator?

**Expected logs:**
```
[DEBUG] Meeting notes available (250 chars): PhoneSwapRequest feature...
[DEBUG] RAG context available (1500 chars)
[DEBUG] Context added: meeting_notes=250 chars, rag=1500 chars, requirements=0
```

**If missing:**
- Agent has context but not passing it
- Check lines 721-722 in universal_agent.py

### Check 3: Is Smart Generator Building Full Prompt?

**Expected behavior:**
```python
full_context_prompt = """
{original prompt}

## Meeting Notes & Requirements
{meeting notes content}

## Retrieved Context (Project Documentation & Patterns)
{RAG context}

## Instructions
Generate the erd using ALL the context above.
Make it specific to this project, not generic.
"""
```

**If missing:**
- `_build_context_prompt()` not being called
- Check line 540 in smart_generation.py

### Check 4: Is Full Context Reaching AI?

**Expected:**
- Line 591: `prompt=full_context_prompt` (NOT just `prompt`)
- AI sees meeting notes + RAG context in prompt

**If AI getting generic prompt:**
- Check if `full_context_prompt` is actually used
- May be using old `prompt` variable

### Check 5: Are Cloud Responses Being Saved?

**Expected:**
```
[CLOUD_FALLBACK] ☁️ All local models below threshold - using cloud fallback...
[CLOUD_FALLBACK] Quality: 92/100
💾 Saved cloud response for fine-tuning (quality: 92/100)
[FINETUNING] Saved cloud response: erd_20251110_105830_123456.json
```

**File created:**
- `finetune_datasets/cloud_responses/erd_YYYYMMDD_HHMMSS_MMMMMM.json`

**If missing:**
- Line 775 `_save_for_finetuning()` not being called
- Check exception handling

### Check 6: Is Gemini Used for Complex Tasks?

**Expected for architecture/prototype:**
```
[SMART_ROUTING] 🎯 Complex task 'architecture' → Using Gemini 2.0 Flash
[CLOUD] ✅ Success with Gemini
```

**If using Groq instead:**
- cloud_fallback_fn not checking task type
- Check lines 648-699 in universal_agent.py

### Check 7: Is Batch Generation Continuing After Failures?

**Expected:**
```
⏳ Generating erd...
✅ erd complete
⏳ Generating architecture...
❌ architecture failed: Validation error
⏳ Generating api_docs...  ← CONTINUES
✅ api_docs complete
```

**If stops early:**
- Exception not caught
- Check lines 2718-2728 in app_v2.py

---

## 🐛 Common Issues & Root Causes

### Issue: "Generations are generic"

**Root causes (in order of likelihood):**

1. **RAG context empty** 
   - ChromaDB not indexed
   - No files in `inputs/` directory
   - Tool excluding everything (over-aggressive filtering)

2. **RAG context not reaching smart generator**
   - `agent.rag_context` set but not passed in line 722
   - Check if parameter name matches

3. **Smart generator not using full_context_prompt**
   - Line 591 using `prompt` instead of `full_context_prompt`
   - Variable name typo

4. **Smart generator not being called at all**
   - Using old generation path
   - `self.smart_generator` is None

### Issue: "Cloud responses not recorded"

**Root causes:**

1. **`_save_for_finetuning()` never called**
   - Line 775 in try/except that's catching exception
   - Cloud fallback doesn't reach that code path

2. **Exception in save method**
   - Directory doesn't exist
   - Permission error
   - JSON serialization error

3. **Wrong code path**
   - Using OLD cloud fallback that doesn't save
   - Check if multiple generation paths exist

### Issue: "Gemini not called"

**Root causes:**

1. **Task not in COMPLEX_TASKS list**
   - artifact_type name mismatch
   - Check line 649-654 in universal_agent.py

2. **Gemini key not configured**
   - Returns early at line 689
   - Falls back to current provider

3. **cloud_fallback_fn not being called**
   - Local models succeeding (false positive)
   - Validation too lenient

---

## 🔧 Quick Fixes

### Fix 1: Add Debug Logging

Add to `smart_generation.py` line 540 (after `_build_context_prompt`):

```python
full_context_prompt = self._build_context_prompt(...)

# DEBUG: Print what we're sending to AI
print(f"[DEBUG_PROMPT] Full prompt length: {len(full_context_prompt)} chars")
print(f"[DEBUG_PROMPT] Contains meeting notes: {'Meeting Notes' in full_context_prompt}")
print(f"[DEBUG_PROMPT] Contains RAG context: {'Retrieved Context' in full_context_prompt}")
print(f"[DEBUG_PROMPT] First 500 chars:\n{full_context_prompt[:500]}")
```

### Fix 2: Verify Context Passing

Add to `universal_agent.py` line 721:

```python
# Before calling smart_generator.generate():
print(f"[DEBUG_AGENT] About to call smart_generator with:")
print(f"  - meeting_notes: {len(self.meeting_notes)} chars")
print(f"  - rag_context: {len(self.rag_context or '')} chars")
print(f"  - feature_requirements: {len(self.feature_requirements or {})} items")
```

### Fix 3: Verify Fine-tuning Save

Add to `smart_generation.py` line 775:

```python
try:
    await self._save_for_finetuning(...)
    print(f"[DEBUG_FINETUNE] ✅ Successfully saved to {self.finetuning_data_dir}")
except Exception as e:
    print(f"[DEBUG_FINETUNE] ❌ Failed to save: {e}")
    import traceback
    traceback.print_exc()
```

---

## 📋 Verification Commands

Run these to check system state:

```bash
# Check if RAG index exists
ls -lh rag/index/

# Check if cloud responses being saved
ls -lh finetune_datasets/cloud_responses/

# Check recent generation logs
tail -n 100 logs/architect_ai.log

# Verify Ollama models
curl http://localhost:11434/api/tags

# Test RAG retrieval
python -c "
from rag.retrieve import retrieve_context
result = retrieve_context('test query', max_chunks=5)
print(f'Retrieved {len(result)} chars')
"
```

---

## 🎯 Action Plan

1. **Add debug logging** (5 min)
   - smart_generation.py: line 540 (prompt building)
   - universal_agent.py: line 721 (before smart_gen call)
   - smart_generation.py: line 775 (finetuning save)

2. **Run test generation** (2 min)
   - Generate ERD
   - Check terminal logs
   - Verify debug output

3. **Identify failing point** (1 min)
   - Which debug log is missing?
   - That's where the issue is

4. **Apply targeted fix** (10 min)
   - Based on which check failed
   - Test again

5. **Verify all systems** (5 min)
   - Test batch generation
   - Check cloud fallback
   - Verify file outputs

---

## 🚀 Expected Output After Fix

```
[HH:MM:SS] 🧠 Intelligent RAG: 18 chunks, 3000 tokens
[DEBUG_AGENT] About to call smart_generator with:
  - meeting_notes: 250 chars
  - rag_context: 1500 chars
  - feature_requirements: 3 items

============================================================
[SMART_GEN] Starting generation for: erd
============================================================

[DEBUG_PROMPT] Full prompt length: 2100 chars
[DEBUG_PROMPT] Contains meeting notes: True
[DEBUG_PROMPT] Contains RAG context: True
[DEBUG_PROMPT] First 500 chars:
Generate a Mermaid ERD diagram...

## Meeting Notes & Requirements
PhoneSwapRequest feature for device exchange...

## Retrieved Context (Project Documentation & Patterns)
class PhoneSwapRequest extends Model {...}

🎯 Using 2 local model(s): mistral:7b-instruct-q4_K_M, llama3.2:3b
📋 Validation: ERD | Quality threshold: 80/100

🔄 Attempt 1/2: Trying mistral:7b-instruct-q4_K_M...
⏳ Loading model mistral:7b-instruct-q4_K_M...
🤖 Generating with mistral:7b-instruct-q4_K_M...
🔍 Validating output from mistral:7b-instruct-q4_K_M...
📊 Quality: 88/100 (threshold: 80)
✅ SUCCESS! mistral:7b-instruct-q4_K_M met quality threshold (88≥80)

[SMART_GEN] ✅ Success! Model: mistral:7b-instruct-q4_K_M, Quality: 88/100, Cloud: False
```

This is what success looks like! 🎉

