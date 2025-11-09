# 🧪 COMPREHENSIVE TESTING GUIDE - November 9, 2025 (FINAL)

## 🎯 Objective

Verify that all critical fixes work correctly:
1. Quality scores reach 80+/100 (not 70/100)
2. Cloud fallback succeeds (no context length errors)
3. Visual prototype generates (no rerun interruption)
4. Outputs are high-quality and context-aware

---

## 🔧 Pre-Test Setup

### Step 1: Restart Application
```bash
# Stop current Streamlit instance (Ctrl+C)
# Then restart:
python launch.py
```

### Step 2: Clear Browser Cache
```
Press: Ctrl + Shift + R (hard refresh)
Or: Clear cache in browser settings
```

### Step 3: Verify API Keys
```bash
python -c "from config.secrets_manager import api_key_manager; print('OpenAI:', api_key_manager.get_key('openai')[:10] + '...'); print('Groq:', api_key_manager.get_key('groq')[:10] + '...'); print('Gemini:', api_key_manager.get_key('gemini')[:10] + '...')"
```

Expected output:
```
OpenAI: sk-proj-...
Groq: gsk_...
Gemini: AIza...
```

If any key is `None`, add it to `.env` file.

---

## 📋 Test Cases

### Test 1: ERD Generation (Cloud Fallback Test)

**Purpose**: Verify context compression works and cloud fallback succeeds

**Steps**:
1. Go to "Generate" tab
2. Click "🏗️ Generate ERD"
3. Watch terminal logs

**Expected Logs**:
```bash
[MODEL_ROUTING] Trying LOCAL model for erd...
[VALIDATION] Local model quality: 70.0/100
[MODEL_ROUTING] ⚠️ Local model quality too low (70.0/100 < 80). Falling back to cloud...
[CONTEXT_COMPRESSION] Reduced prompt from 37931 to 11500 chars (30.3% retained)
[CONTEXT_COMPRESSION] Estimated tokens: ~2875 (target: 3000)
[OK] Cloud fallback succeeded using Groq
# OR [OK] Cloud fallback succeeded using Gemini
# OR [OK] Cloud fallback succeeded using OpenAI GPT-4
```

**Expected UI**:
- Quality Score: 🟢 80-95/100 (NOT 70/100)
- Validation: ✅ PASS
- Message: "✅ ERD generated!"

**Success Criteria**:
- ✅ Cloud fallback succeeds (no `context_length_exceeded` error)
- ✅ Quality score >= 80
- ✅ Context compressed to ~12K chars

**Failure Indicators**:
- ❌ "Error code: 400 - context_length_exceeded" → Context still too large
- ❌ Quality score = 70/100 → Cloud fallback failed, showing local result
- ❌ "All cloud providers failed" → API key issue

---

### Test 2: Architecture Diagram Generation

**Purpose**: Verify model routing and quality thresholds

**Steps**:
1. Go to "Generate" tab
2. Click "🏛️ Generate Architecture"
3. Watch terminal logs

**Expected Logs**:
```bash
[MODEL_ROUTING] Trying LOCAL model for architecture...
[INFO] Model llama3:8b-instruct-q4_K_M already loaded
[VALIDATION] Local model quality: 77.0/100
[MODEL_ROUTING] ⚠️ Local model quality too low (77.0/100 < 80). Falling back to cloud...
[CONTEXT_COMPRESSION] Compressed: 40195 → 12000 chars (29.8% retained)
[OK] Cloud fallback succeeded using Gemini
```

**Expected UI**:
- Quality Score: 🟢 80-95/100
- Validation: ✅ PASS
- Interactive HTML visualization loads (not generic fallback)

**Success Criteria**:
- ✅ Quality >= 80
- ✅ HTML visualization is context-aware (shows actual project components)
- ✅ No static fallback warning

---

### Test 3: Batch Artifact Generation

**Purpose**: Verify system handles multiple artifacts without errors

**Steps**:
1. Go to "Generate" tab
2. Click "📦 Generate: ERD, Architecture, All Diagrams, API Docs, JIRA, Workflows..."
3. Watch terminal logs for all 10 artifacts

**Expected Behavior**:
- Some artifacts (ERD, Architecture) fall back to cloud → 80+ scores
- Some artifacts (JIRA, Workflows) may pass locally → 80+ scores
- ALL artifacts complete successfully (no skips except ERD/Architecture if cloud fails)

**Expected UI**:
- Progress: "📝 Generating 1/10: Erd..." → "📝 Generating 10/10: Workflows..."
- All quality scores: 80-95/100
- Success message: "✅ All 10 artifacts generated successfully!"

**Success Criteria**:
- ✅ All artifacts generate (no "❌ Error generating..." except cloud fallback attempts)
- ✅ Quality scores >= 80
- ✅ No `context_length_exceeded` errors

**Failure Indicators**:
- ❌ "❌ Error generating erd: All cloud providers failed" → Check API keys
- ❌ Some artifacts skip → Rate limit or API issue
- ❌ Quality scores = 70/100 → Cloud fallback not working

---

### Test 4: Prototype Generation (Rerun Test)

**Purpose**: Verify visual prototype generates without rerun interruption

**Steps**:
1. Go to "Generate" tab
2. Enter meeting notes (min 80 chars)
3. Click "🎨 Generate: Code & Visual Prototypes..."
4. Watch terminal logs

**Expected Logs**:
```bash
🎨 Generating 2 prototypes...

📝 Generating 1/2: Code Prototype...
[INFO] Generating code prototype...
[DEBUG] Tech stacks detected: ['Angular', 'TypeScript', '.NET', 'C#']
✅ Generated 9 code files

📝 Generating 2/2: Visual Prototype...
[MODEL_ROUTING] Trying LOCAL model for visual_prototype_dev...
[VALIDATION] Local model quality: 75.0/100
[MODEL_ROUTING] ⚠️ Local model quality too low (75.0/100 < 80). Falling back to cloud...
[CONTEXT_COMPRESSION] Compressed: 36906 → 11000 chars
[OK] Cloud fallback succeeded using Gemini
✅ Generated custom HTML visualization
```

**Expected UI**:
- Progress bar shows 1/2 → 2/2
- Success messages for BOTH prototypes:
  - "✅ Generated 9 code files"
  - "✅ Visual Prototype generated!"
- Outputs tab shows both:
  - 💻 Code Prototype (9 files)
  - 🎨 Visual Prototype (HTML)

**Success Criteria**:
- ✅ Code prototype generates (9 files)
- ✅ Visual prototype ALSO generates (no rerun interruption)
- ✅ Both appear in Outputs tab
- ✅ HTML visualization is context-aware (not generic)

**Failure Indicators**:
- ❌ Only code prototype appears → `st.rerun()` still happening
- ❌ Visual prototype missing → Check for rerun at line 4959
- ❌ HTML is generic → Cloud fallback failed

---

### Test 5: HTML Visualization Quality

**Purpose**: Verify HTML is context-aware and not generic

**Steps**:
1. Generate any diagram (ERD, Architecture, etc.)
2. Go to "Outputs" tab
3. Click on diagram → "🌐 HTML Visualization"
4. Click "Generate Visual Editor" (optional)

**Expected HTML**:
- Shows actual project components (UserController, WeatherForecastController, etc.)
- Uses repository context (not generic placeholders)
- Interactive elements work (hover, click)

**Generic HTML Example (SHOULD NOT SEE)**:
```html
<h1>Repository Context Visualization</h1>
<div class="node">
  <h3>Controllers</h3>
  <p>WeatherForecastController</p>
  <p>UsersController</p>
</div>
```

**Context-Aware HTML Example (SHOULD SEE)**:
```html
<h1>Registration API Architecture</h1>
<div class="component">
  <h3>UserController</h3>
  <p>Endpoints: GET /users, POST /users/register</p>
  <p>Dependencies: UserService, MongoDB</p>
</div>
```

**Success Criteria**:
- ✅ HTML mentions actual project names (registration-api, UserController, etc.)
- ✅ Shows real endpoints and models from codebase
- ✅ NOT generic content

---

## 📊 Expected Metrics

| Test Case | Expected Quality Score | Expected Cloud Usage | Expected Time |
|-----------|------------------------|----------------------|---------------|
| ERD Generation | 80-95/100 | Yes (fallback) | 20-30s |
| Architecture | 80-95/100 | Yes (fallback) | 25-35s |
| Batch (10 artifacts) | 80-95/100 avg | 2-4 artifacts | 3-5 min |
| Code Prototype | 80-95/100 | No (codellama passes) | 30-45s |
| Visual Prototype | 80-95/100 | Yes (llama3 fallback) | 20-30s |

---

## 🐛 Troubleshooting

### Issue: Quality scores still 70/100

**Diagnosis**: Cloud fallback not working

**Checks**:
```bash
# 1. Check API keys
python -c "from config.secrets_manager import api_key_manager; print(api_key_manager.get_key('openai'))"

# 2. Check logs for errors
grep "Cloud provider.*failed" terminal_output.log

# 3. Check context compression
grep "CONTEXT_COMPRESSION" terminal_output.log
```

**Expected**: 
- API keys exist and are valid
- Cloud providers succeed (Groq, Gemini, or OpenAI)
- Context compressed to ~12K chars

**Fix**:
- If API keys missing → Add to `.env`
- If context too large → Reduce `max_tokens` further to 2500
- If all cloud providers fail → Check internet connection

---

### Issue: Visual prototype missing

**Diagnosis**: `st.rerun()` still happening

**Checks**:
```bash
# Search for rerun in prototype generation code
grep -n "st.rerun()" architect_ai_cursor_poc/app/app_v2.py | grep -A 5 -B 5 4959
```

**Expected**: Line 4959 should have comment: `# Removed st.rerun() to allow visual prototype to generate`

**Fix**:
```python
# Line 4956-4959
st.success("✅ Outputs generated! Switch to 'Outputs' tab to view them.")

# Removed st.rerun() to allow visual prototype to generate
```

---

### Issue: Context length exceeded errors persist

**Diagnosis**: Compression not aggressive enough

**Checks**:
```bash
# Look for estimated tokens in logs
grep "Estimated tokens" terminal_output.log
```

**Expected**: `~2875 (target: 3000)`

**If > 3000 tokens**, reduce further:
```python
# In ai/smart_model_selector.py line 373
async def compress_prompt_for_cloud(prompt: str, max_tokens: int = 2500):  # Reduce from 3000
```

---

### Issue: HTML still generic

**Diagnosis**: Cloud models not generating HTML

**Checks**:
```bash
# Check HTML generation logs
grep "MODEL_ROUTING.*visual_prototype_dev" terminal_output.log
grep "Cloud fallback succeeded" terminal_output.log
```

**Expected**: 
```
[MODEL_ROUTING] Trying LOCAL model for visual_prototype_dev...
[MODEL_ROUTING] ⚠️ Local model quality too low...
[OK] Cloud fallback succeeded using Gemini
```

**Fix**: Ensure `llama3:8b-instruct-q4_K_M` model is available or cloud fallback triggers

---

## ✅ Final Checklist

After running all tests, verify:

- [ ] All quality scores >= 80/100
- [ ] No `context_length_exceeded` errors in logs
- [ ] Cloud providers succeed (Groq/Gemini/OpenAI)
- [ ] Context compressed to ~12K chars (3000 tokens)
- [ ] Visual prototype generates (no rerun)
- [ ] HTML visualizations are context-aware
- [ ] Batch generation completes all artifacts
- [ ] No "All cloud providers failed" errors

**If ALL checkboxes checked → System is working correctly ✅**

---

## 📞 Contact

If tests fail after following this guide, provide:
1. Complete terminal logs (last 100 lines)
2. Screenshot of UI (quality scores, errors)
3. Result of API key check command
4. Which test case failed

---

**Last Updated**: November 9, 2025
**Version**: Final (Post-Critical Fixes)

