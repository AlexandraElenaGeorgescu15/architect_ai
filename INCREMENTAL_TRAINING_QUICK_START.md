# 🚀 Incremental Training - Quick Start

## What You Asked For
> "I want fine-tuning to build on previous training, not start from scratch each time"

## What You Got ✅

**TRUE INCREMENTAL TRAINING!** Each training run now builds on the previous one.

---

## How It Works (Simple Version)

### Before:
```
Run 1: Base → Train → v1 ❌ Discarded
Run 2: Base → Train → v2 ❌ Discarded  
Run 3: Base → Train → v3 ✅ Only this one matters
```

### Now:
```
Run 1: Base → Train → v1 ✅ Saved
Run 2: v1 → Train → v2   ✅ Builds on v1
Run 3: v2 → Train → v3   ✅ Builds on v2
```

**Result**: v3 contains improvements from v1 + v2 + v3! 🎉

---

## How To Use It (3 Steps)

### Step 1: Load Model
1. Go to **Fine-Tuning** tab
2. Click **"🔄 Load"** on Codellama-7b
3. Wait for it to load

**You'll see**:
- First time: "🆕 **Base Mode:** Next training will be v1"
- After training: "🔄 **Incremental Mode:** Loaded v1_TIMESTAMP"

### Step 2: Train
1. Enter meeting notes
2. Check "🚀 Unlimited Mode"
3. Click "Preview Dataset"
4. Click "🚀 Start Fine-Tuning"

**Logs will show**:
```
[INCREMENTAL] Training v1_20251105_140000 (builds on base model)
```

### Step 3: Give Feedback & Train Again
1. Generate some artifacts (ERD, API, prototype)
2. Click "👍 Good" or "👎 Needs Improvement"
3. Go back to Fine-Tuning tab
4. Click "Preview Dataset" (see your feedback added!)
5. Click "🚀 Start Fine-Tuning" again

**Logs will show**:
```
[INCREMENTAL] Loading previous fine-tuned model: v1_20251105_140000
[INCREMENTAL] ✅ Successfully loaded fine-tuned model!
[INCREMENTAL] Training v2_20251105_153000 (builds on v1_20251105_140000)
```

**That's it!** v2 now contains all improvements from v1 + your new feedback! 🚀

---

## Bonus: Rollback Feature

### What if v3 was trained badly?

1. Go to Fine-Tuning tab
2. Expand **"View all versions / Rollback"**
3. Click **"Load"** next to v2 (the good one)
4. Train again → Creates v4 (builds on v2, skips bad v3)

**You're back on track!** 🎯

---

## Key Features

1. **✅ Automatic** - System detects and loads latest version
2. **✅ Cumulative** - Each run builds on previous improvements
3. **✅ Versioned** - Every training creates a new version (v1, v2, v3...)
4. **✅ Rollback** - Load any previous version if needed
5. **✅ Safe** - Never overwrites existing versions

---

## What Changed in the Code?

**You don't need to know this, but if you're curious**:

1. **`load_model()`** now checks for existing fine-tuned versions and loads the latest
2. **Version names** are auto-generated: `vN_YYYYMMDD_HHMMSS`
3. **Training saves** to version-specific folders: `finetuned_models/codellama-7b/v1_TIMESTAMP/`
4. **UI shows** current version status and lists all available versions
5. **Rollback** is a simple button click to load any previous version

---

## Logs To Watch For

### When Loading Model (First Time):
```
[INFO] Loading base model (no previous fine-tuning found)
[DEBUG] Model loaded successfully (base model)!
```

### When Loading Model (After Training):
```
[INCREMENTAL] Loading previous fine-tuned model: v2_20251105_153000
[INCREMENTAL] ✅ Successfully loaded fine-tuned model!
[INCREMENTAL] Next training will build on: v2_20251105_153000
[DEBUG] Model loaded successfully (incremental from v2_20251105_153000)!
```

### When Training:
```
[INCREMENTAL] Training v3_20251105_160000 (builds on v2_20251105_153000)
```

---

## Expected Workflow

```
Day 1:
  Load base → Train → v1 created
  ✅ Model learns your codebase patterns

Day 2:
  Generate artifacts → Give feedback (5 entries)
  Load v1 → Train → v2 created
  ✅ Model improves with v1 knowledge + new feedback

Day 3:
  Generate more → Give more feedback (8 entries total)
  Load v2 → Train → v3 created
  ✅ Model is now significantly better (v1 + v2 + new feedback)

Day 4:
  Notice v3 is worse → Rollback to v2
  Load v2 → Add feedback (12 entries total)
  Load v2 → Train → v4 created
  ✅ Back on track with good v2 + corrections
```

---

## File Structure

```
finetuned_models/
└── codellama-7b/
    ├── v1_20251105_140000/     ← First training
    │   ├── adapter_config.json
    │   └── adapter_model.bin    (100-200MB)
    ├── v2_20251105_153000/     ← Builds on v1
    │   ├── adapter_config.json
    │   └── adapter_model.bin
    └── v3_20251105_160000/     ← Builds on v2
        ├── adapter_config.json
        └── adapter_model.bin
```

**Note**: Each version is only ~100-200MB (LoRA adapters, not full models).

---

## Quick Troubleshooting

### "Still showing Base Mode after training"
→ **Restart the app!** The old code is still running.

### "Can't see version list"
→ **Train at least once first.** Versions appear after first training.

### "Training takes forever"
→ **Normal!** Training takes 30-60 minutes. But quality improves faster now because you start from a better baseline each time.

### "Want to start completely fresh"
→ Delete `finetuned_models/codellama-7b/` folder, then reload the model. It will start from base again.

---

## 🎉 You're Done!

**Restart the app and try it out!**

1. **Restart**: `Ctrl+C` → `python launch.py`
2. **Load model**: Fine-Tuning tab → Click "Load"
3. **Check status**: Should show "Base Mode" or "Incremental Mode"
4. **Train once**: Create v1
5. **Train again**: Creates v2 (builds on v1!)

**Your model will now continuously improve with each iteration!** 🚀

---

**For more details**: Read `INCREMENTAL_TRAINING_GUIDE.md` (complete guide with examples and FAQ).

