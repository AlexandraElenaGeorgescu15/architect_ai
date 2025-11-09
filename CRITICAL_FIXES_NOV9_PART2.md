# Critical Fixes Needed - Part 2 (November 9, 2025)

## 🔴 Issues from Terminal Output

### 1. **Cloud Provider Failures** (HIGH PRIORITY)
**Error:** `All cloud providers failed. Please check API keys in secrets store.`

**Details:**
- Gemini: `CLOUD_FALLBACK` error (API key exists but not working)
- OpenAI: Context length exceeded (12180 tokens requested, 8192 max)

**Root Causes:**
- Gemini API key may not be properly loaded/formatted
- OpenAI prompt truncation not aggressive enough

---

### 2. **RuntimeWarning: Coroutine Never Awaited** (MEDIUM PRIORITY)
**Warning:** `RuntimeWarning: coroutine 'MermaidSyntaxCorrector.correct_diagram' was never awaited`

**Location:** `output_validator.py:218` and `output_validator.py:322`

**Root Cause:** Calling async function without `await` in synchronous context

---

### 3. **Generic Content Still Being Generated** (HIGH PRIORITY)
**Issue:** Architecture diagram got 0/100 score with "Multiple placeholder nodes detected (8)"

**Details:**
- Despite entity extraction working (`[CODE_GEN] ✅ Extracted 3 entities from ERD: User, RequestSwap, MeetingNote`)
- All other diagrams scoring only 70/100 (medium quality)
- Local models generating generic "Node A", "Node B" content

---

### 4. **Visual Prototype Not Generating** (MEDIUM PRIORITY)
**Issue:** User reports visual prototype doesn't generate when clicking "Generate Prototypes"

**Suspected Causes:**
- Button code looks correct (lines 2845-2870)
- May be failing silently in `_dispatch()` function
- Or visual_prototype_dev generation itself is crashing

---

### 5. **All Artifacts Scoring 70/100** (MEDIUM PRIORITY)
**Issue:** Every artifact (System Overview, Data Flow, User Flow, Components, API Sequence, API Docs, JIRA, Workflows) scored exactly 70/100

**Indicates:**
- Prompts not strong enough
- Local models producing mediocre output
- Validation may be too lenient

---

## 🔧 Fix Plan

### Fix 1: Gemini API Key Loading
**File:** `agents/universal_agent.py` or `config/api_key_manager.py`

**Action:**
1. Verify Gemini API key is being loaded correctly
2. Check key format (should start with "AIzaSy")
3. Test Gemini API call directly
4. Add better error messages

**Expected Result:**
- Gemini fallback works
- Better error messages if key invalid

---

### Fix 2: OpenAI Context Truncation
**File:** `agents/universal_agent.py` → `_call_ai()` method

**Current:** Truncates to ~23K characters (still too much)
**New:** More aggressive truncation:
- For ERD/Architecture: Limit to 15K characters
- For API Docs: Limit to 12K characters
- For Diagrams: Limit to 10K characters

**Expected Result:**
- OpenAI calls succeed
- Context length under 8192 tokens

---

### Fix 3: MermaidSyntaxCorrector Async Fix
**File:** `validation/output_validator.py` lines 218, 322

**Current:**
```python
pass  # RuntimeWarning: coroutine not awaited
```

**New:**
```python
# Sync validation - skip async syntax correction
# (Syntax correction happens separately after validation)
pass
```

**Expected Result:**
- No more RuntimeWarnings
- Validation still works

---

### Fix 4: Strengthen Diagram Prompts
**File:** `agents/universal_agent.py` → All diagram generation methods

**Changes:**
- Add "YOU WILL BE PENALIZED FOR GENERIC CONTENT" warning
- Repeat entity names 3 times in prompt
- Add validation check in prompt: "Does your diagram use ACTUAL entities?"
- Increase penalty for placeholder nodes in validation

**Expected Result:**
- Diagrams use actual entities
- Scores above 80/100

---

### Fix 5: Visual Prototype Debugging
**File:** `app/app_v2.py` → `_dispatch()` function

**Actions:**
1. Add explicit logging for visual_prototype_dev
2. Check if generation succeeds but file save fails
3. Verify file path is correct
4. Add error handling

**Expected Result:**
- Visual prototype generates successfully
- Clear error messages if it fails

---

## 📊 Expected Improvements

| Issue | Before | After |
|-------|--------|-------|
| Gemini Fallback | ❌ Failing | ✅ Working |
| OpenAI Context | ❌ Exceeds limit | ✅ Within limit |
| RuntimeWarning | ⚠️ Constant warnings | ✅ No warnings |
| Diagram Quality | 🔴 0-70/100 | 🟢 80-95/100 |
| Generic Content | ❌ Frequent | ✅ Rare |
| Visual Prototype | ❌ Not generating | ✅ Generates |

---

## 🧪 Testing Checklist

After fixes:
- [ ] Generate ERD → Should use Gemini/OpenAI fallback successfully
- [ ] Generate Architecture → Should score 80+ and use actual entities
- [ ] Generate All Artifacts → No RuntimeWarnings in console
- [ ] Generate Prototypes → Visual prototype generates
- [ ] Check console → No "coroutine never awaited" warnings

---

## 💡 Quick Wins (Do These First)

1. **Fix MermaidSyntaxCorrector warning** (5 minutes)
   - Comment out the async call in validation
   - Add explanation

2. **Verify Gemini API key** (5 minutes)
   - Print key (first 20 chars) to verify it's loaded
   - Test direct Gemini API call

3. **More aggressive OpenAI truncation** (10 minutes)
   - Reduce max_chars from 23K to 12K
   - Add artifact-specific limits

4. **Add visual prototype logging** (5 minutes)
   - Log when visual_prototype_dev starts
   - Log file save location
   - Log any errors

---

## 🎯 Priority Order

1. **HIGH:** Fix Gemini API key loading (blocking cloud fallback)
2. **HIGH:** Strengthen diagram prompts (quality issue)
3. **MEDIUM:** Fix RuntimeWarning (annoying but not breaking)
4. **MEDIUM:** More aggressive OpenAI truncation (affects fallback)
5. **MEDIUM:** Debug visual prototype generation (feature incomplete)

---

**Estimated Time:** 1-2 hours for all fixes
**Impact:** Critical - Makes cloud fallback work, improves quality dramatically

