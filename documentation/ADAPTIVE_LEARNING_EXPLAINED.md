# 🎯 ADAPTIVE LEARNING: How It Works

## What Actually Learns?

### **SHORT ANSWER:**
The system records feedback for ALL models (local + cloud), but **fine-tuning only works for LOCAL Ollama models**.

---

## 📊 Learning by Model Type

### **1. LOCAL OLLAMA MODELS (CodeLlama, Mistral, etc.)**
✅ **Semi-Automatic Learning Pipeline:**
- Feedback recorded ✅ (AUTOMATIC)
- Training batches created ✅ (AUTOMATIC - 5000+ examples)
- Model fine-tuned ⚠️ (MANUAL - requires button click)
- Quality improves over time ✅ (after manual training)

**How it works:**
```
User Request → CodeLlama → Validation → Feedback (AUTOMATIC)
                                           ↓
                            Training Batch (5000+ examples) (AUTOMATIC)
                                           ↓
                            User Clicks "Start Fine-Tuning" (MANUAL)
                                           ↓
                            Fine-Tune CodeLlama (AUTOMATIC ONCE STARTED)
                                           ↓
                            Better CodeLlama Model
```

**What you get:**
- Model learns YOUR codebase patterns
- Generates code in YOUR style
- Understands YOUR architecture
- Improves with every use

---

### **2. CLOUD MODELS (GPT-4, Gemini, Groq)**
⚠️ **Partial Learning:**
- Feedback recorded ✅ (AUTOMATIC)
- Training batches created ✅ (AUTOMATIC - 5000+ examples)
- Model fine-tuned ❌ (can't fine-tune cloud models - you don't own them)
- Prompt improvement ⏳ (not implemented yet, but data is ready)

**Current behavior:**
```
User Request → GPT-4 → Validation → Feedback (AUTOMATIC)
                                      ↓
                        Training Batch Created (AUTOMATIC)
                                      ↓
                        Saved for Future Use (5000+ examples ready)
                        (Can't fine-tune GPT-4 - you don't own it)
```

**What you get:**
- Feedback tracking (know what works/doesn't)
- Training dataset (ready if you install Ollama)
- Quality metrics (see which artifacts need work)

**What you DON'T get:**
- Model fine-tuning (you don't own cloud models)
- Automatic improvement (GPT-4 stays same)

---

## 🤔 So What's the Point If I Use Cloud Models?

### **1. Prompt Improvement (Coming Soon)**
Even though we can't fine-tune GPT-4, we can use feedback to:
- Learn which prompts work best
- Add successful examples to prompts (few-shot learning)
- Optimize system prompts based on validation scores

**Example:**
```python
# BAD PROMPT (validation score: 60/100)
"Generate an ERD"

# LEARNED PROMPT (validation score: 90/100)
"Generate an ERD with:
- All relationships explicitly labeled
- Primary/foreign keys clearly marked
- Based on these successful patterns: [examples from training batch]"
```

### **2. Future Local Models**
If you later install Ollama:
- Training data already collected ✅
- Ready to fine-tune immediately ✅
- No data loss ✅

### **3. Quality Metrics**
Track which artifact types need improvement:
```
ERD: 85/100 (good)
Architecture: 65/100 (needs work)
API Docs: 90/100 (excellent)
```

---

## 🚀 Recommended Setup

### **Option 1: BEST EXPERIENCE (Local + Cloud)**
```
1. Install Ollama (free, runs locally)
2. Configure cloud models as fallback
3. Get full learning pipeline
```

**Benefits:**
- ✅ Models fine-tune automatically
- ✅ Fast local generation (most requests)
- ✅ Cloud fallback (complex requests)
- ✅ Cost savings (less cloud usage over time)

**Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull codellama:7b-instruct
ollama pull mistral:7b-instruct

# Launch Architect.AI
streamlit run app/app_v2.py
```

---

### **Option 2: CLOUD ONLY (Feedback Tracking)**
```
1. Use GPT-4/Gemini/Groq only
2. Feedback recorded but not used for fine-tuning
3. Can upgrade to Option 1 later
```

**Benefits:**
- ✅ No local setup needed
- ✅ Feedback tracked for future use
- ✅ Can switch to local later

**Current Limitation:**
- ❌ No automatic model improvement
- ❌ Training data collected but not used
- ❌ Cloud costs stay constant

---

## 🔧 What We Should Add (Improvements)

### **For Cloud Models:**
1. **Prompt Learning** - Use feedback to optimize prompts
2. **Few-Shot Learning** - Add best examples to prompts
3. **Quality-Based Routing** - Route to best model per artifact type

### **Implementation:**
```python
# In _call_ai method:
if self.client_type in ['openai', 'gemini', 'groq']:
    # Get best examples from training batch
    best_examples = self.adaptive_loop.get_best_examples(
        artifact_type=artifact_type,
        min_score=80.0,
        limit=3
    )
    
    # Enhance prompt with successful examples
    prompt = self._enhance_prompt_with_examples(prompt, best_examples)
```

This way, even cloud models benefit from learning!

---

## 📊 Current Status

### **What Works Now:**
- ✅ Feedback recording (all models, automatic)
- ✅ Reward calculation (all models, RL-based, -1 to +1, automatic)
- ✅ Training batch creation (all models, 5000+ examples, automatic)
- ✅ Fine-tuning (LOCAL Ollama models only, **MANUAL TRIGGER - button click**)
- ✅ Incremental training (v1 → v2 → v3, loads previous version)
- ✅ Checkpointing (survives app restarts)

### **What's Missing:**
- ⏳ Automatic training trigger (currently requires manual button click)
- ⏳ Prompt learning for cloud models (use feedback to optimize prompts)
- ⏳ Few-shot learning integration (add best examples to prompts)
- ⏳ Quality-based routing (route to best model per artifact type)

### **Important Clarification:**
The fine-tuning pipeline has **automatic feedback collection** but requires a **manual training trigger** (button click in Fine-Tuning tab). This prevents unsafe automatic model updates in production.

### **Recommendation:**
Install Ollama to get the full learning experience. It's:
- Free ✅
- Fast ✅
- Runs locally ✅
- Learns from YOUR code ✅
- Requires manual training trigger (safety) ✅

---

## 🎯 Summary

**Q: What model learns?**
**A:** LOCAL Ollama models (CodeLlama, Mistral, etc.)

**Q: What if I only use cloud models?**
**A:** Feedback is recorded but not used for fine-tuning (yet). We should add prompt learning.

**Q: Should I install Ollama?**
**A:** YES! It's free and gives you the full learning pipeline.

**Q: Can I use both?**
**A:** YES! Best setup = Local (most requests) + Cloud (fallback for complex tasks)

---

## 💡 Next Steps

1. **Install Ollama** (recommended):
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Windows
   # Download from https://ollama.com/download
   ```

2. **Pull models**:
   ```bash
   ollama pull codellama:7b-instruct
   ollama pull mistral:7b-instruct
   ```

3. **Start learning**:
   ```bash
   streamlit run app/app_v2.py
   ```

4. **Watch models improve**:
   - After 50 examples → First fine-tuned model
   - After 100 examples → Noticeable improvement
   - After 500 examples → Domain expert

---

**Bottom Line:** Right now, learning works best with LOCAL models. If you only use cloud models, feedback is tracked but not actively used (we should add prompt learning for this case).
