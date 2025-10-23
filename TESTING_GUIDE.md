# 🧪 Testing Guide - Architect.AI v2.5.2

## Quick Test Checklist

Use this guide to verify all features work correctly, including the latest v2.5.2 production-ready reliability improvements (cache busting, version flow, portability, and RAG freshness).

---

## Prerequisites

1. ✅ Application running: `python launch.py`
2. ✅ Browser open at: `http://localhost:8501`
3. ✅ API key configured in sidebar
4. ✅ Meeting notes file ready (optional)

---

## Test 1: Code Editor Tab ✏️

**Steps:**
1. Go to Developer Mode
2. Upload meeting notes OR use existing
3. Click **Generate Code Prototype**
4. Wait for generation to complete
5. Go to **Code Editor** tab (Tab 4)
6. Select a code file from dropdown
7. Edit some code in Monaco editor
8. Click **Save Changes**
9. Click **Download** to get file

**Expected Results:**
- ✅ Monaco editor loads without errors
- ✅ Syntax highlighting works
- ✅ Can type and edit code
- ✅ Save shows success message
- ✅ Download works

**If Issues:**
- Check browser console for errors
- Verify code files exist in `outputs/prototypes/`

---

## Test 2: Test Generator Tab 🧪

**Steps:**
1. Ensure you have generated code (from Test 1)
2. Go to **Tests** tab (Tab 5)
3. Select a code file from dropdown
4. Expand "File Preview" to see code
5. Click **Generate Tests**
6. Wait for AI to generate tests
7. Verify tests displayed
8. Check saved file location
9. Click **Download Tests**

**Expected Results:**
- ✅ Lists all code files (no test files)
- ✅ Generates tests successfully
- ✅ **NO ``` html or ``` python markers**
- ✅ Tests saved as `test_*.ext`
- ✅ Download works

**Critical Check:**
Open the downloaded test file and verify:
- ❌ Should NOT start with ` ```python `
- ✅ Should start with actual test code

---

## Test 3: Export Manager Tab 📤

**Steps:**
1. Generate multiple artifacts:
   - ERD
   - Architecture
   - JIRA
   - Visual Prototype
2. Go to **Export** tab (Tab 6)
3. Check stats displayed:
   - Total Files
   - Total Size
   - Categories
4. Click **Export All as ZIP**
5. Click **Download ZIP**
6. Extract ZIP and verify contents
7. Expand a category (e.g., Diagrams)
8. Click individual download (⬇️) button

**Expected Results:**
- ✅ Stats show correct counts
- ✅ ZIP downloads successfully
- ✅ ZIP contains all artifacts
- ✅ Files organized by category
- ✅ Individual downloads work

**Verify ZIP Contents:**
```
architect_ai_export_YYYYMMDD_HHMMSS.zip
├── Diagrams/
│   └── visualizations/
│       ├── erd_diagram.mmd
│       └── architecture_diagram.mmd
├── Documentation/
│   └── documentation/
│       ├── api.md
│       └── jira_tasks.md
├── HTML Prototypes/
│   └── prototypes/
│       └── dev_visual_prototype.html
├── Code Files/
│   └── prototypes/
│       └── (code files)
└── Workflows/
    └── workflows/
        └── workflows.md
```

---

## Test 4: Workspace Cleanup 🗑️

**Steps:**
1. Generate some artifacts (if not already)
2. Look at sidebar
3. Check **Storage Used** metric
4. Note the MB value
5. Click **Clear All Outputs**
6. Wait for success message
7. Check storage metric again
8. Verify **Outputs** tab is empty

**Expected Results:**
- ✅ Storage metric shows size > 0 MB
- ✅ Clear button shows success
- ✅ File count displayed
- ✅ Storage drops to ~0 MB
- ✅ App reloads automatically
- ✅ All outputs cleared

---

## Test 5: PM Mode Input Toggle 💡

**Steps:**
1. Switch to **PM Mode**
2. Go to **Idea** tab
3. Verify radio buttons show:
   - ✍️ Describe Idea
   - 📄 Use Meeting Notes
4. Select **Describe Idea**
5. Type a feature idea
6. Click **Generate Visual Prototype**
7. Wait for completion
8. Go back to **Idea** tab
9. Select **Use Meeting Notes**
10. Verify notes load (if uploaded in Dev mode)
11. Expand preview
12. Click **Generate JIRA Tasks**

**Expected Results:**
- ✅ Radio toggle displays correctly
- ✅ Manual text area works
- ✅ Meeting notes load automatically
- ✅ Preview shows notes content
- ✅ Both generation methods work
- ✅ Success messages show source

---

## Test 6: Markdown Stripping ✨

**This is the CRITICAL test!**

**Steps:**
1. Generate Visual Prototype (Dev OR PM)
2. Open the generated HTML file in text editor
3. Check first 5 lines
4. Generate JIRA tasks
5. Open JIRA markdown file
6. Check first 5 lines
7. Generate tests (from Test 2)
8. Open test file
9. Check first 5 lines

**Expected Results:**

**HTML File (`dev_visual_prototype.html`):**
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
...
```
❌ **Should NOT start with:** ` ```html `

**JIRA File (`dev_jira_tasks.md`):**
```markdown
# JIRA Tasks

## Epic: Feature Name
...
```
❌ **Should NOT start with:** ` ```markdown `

**Test File (`test_something.py`):**
```python
import pytest

def test_something():
...
```
❌ **Should NOT start with:** ` ```python `

**If you see ``` markers:**
- 🐛 This is a bug - the fix didn't apply
- Report which file has the issue

---

## Test 7: Separate Dev/PM Outputs 📁

**Steps:**
1. Go to Developer Mode
2. Generate Visual Prototype
3. Note file created: `outputs/prototypes/dev_visual_prototype.html`
4. Switch to PM Mode
5. Choose "Describe Idea"
6. Type: "User dashboard with charts"
7. Generate Visual Prototype
8. Note file created: `outputs/prototypes/pm_visual_prototype.html`
9. Check both files exist
10. Verify they're different

**Expected Results:**
- ✅ Dev file: `dev_visual_prototype.html`
- ✅ PM file: `pm_visual_prototype.html`
- ✅ Both files exist simultaneously
- ✅ No overwriting
- ✅ Success messages show correct paths

**Verify Files:**
```
outputs/
└── prototypes/
    ├── dev_visual_prototype.html   ← From Developer Mode
    └── pm_visual_prototype.html     ← From PM Mode
```

---

## Test 8: Storage Metrics 📊

**Steps:**
1. Go to sidebar
2. Generate 3-4 artifacts
3. Watch **Storage Used** metric
4. Note value increases
5. Check **Generations** count
6. Check **Features** count
7. Expand **Activity Log**
8. Verify last 10 actions shown

**Expected Results:**
- ✅ Storage metric updates
- ✅ Generations count increases
- ✅ Features count tracks artifacts
- ✅ Activity log shows recent actions
- ✅ All metrics real-time

---

## Test 9: End-to-End Workflow 🔄

**Complete Developer Workflow:**
```
1. Upload meeting notes
2. Generate ERD
3. Generate Architecture
4. Generate JIRA
5. Generate Code Prototype
6. Edit code in Code Editor
7. Generate tests in Tests tab
8. Export all as ZIP
9. Download ZIP
10. Clear workspace
```

**Time:** ~5-10 minutes  
**Artifacts Created:** 7-10 files

**Success Criteria:**
- ✅ All steps complete without errors
- ✅ All artifacts generated correctly
- ✅ No markdown artifacts (```)
- ✅ ZIP contains everything
- ✅ Cleanup works

---

## Test 10: Error Handling 🚨

**Steps:**
1. Try to generate without API key
2. Try to use meeting notes when none uploaded
3. Try to edit code when none generated
4. Try to export when nothing generated
5. Try to generate tests when no code exists

**Expected Results:**
- ✅ Clear error messages
- ✅ Helpful suggestions
- ✅ No crashes
- ✅ App remains functional

---

## Common Issues & Solutions

### Issue 1: Monaco Editor Not Loading
**Symptom:** Code Editor tab shows error or blank

**Solution:**
- Check browser console
- Verify `streamlit.components.v1` available
- Try refreshing browser

### Issue 2: Tests Have ``` Markers
**Symptom:** Test files start with ` ```python `

**Solution:**
- This shouldn't happen! Report as bug
- Manually remove ``` from file
- Check `strip_markdown_artifacts()` is called

### Issue 3: PM/Dev Outputs Conflict
**Symptom:** Files overwrite each other

**Solution:**
- Verify paths in code
- Check `pm_visual_prototype.html` vs `dev_visual_prototype.html`
- Report if still conflicting

### Issue 4: ZIP Export Fails
**Symptom:** ZIP download doesn't work

**Solution:**
- Check outputs directory has files
- Verify disk space
- Try individual downloads first

### Issue 5: Cleanup Doesn't Work
**Symptom:** Files remain after cleanup

**Solution:**
- Check file permissions
- Verify no files are open/locked
- Try manual deletion as test

---

## Performance Benchmarks

**Expected Times:**

| Action | Time |
|--------|------|
| Generate ERD | 10-20s |
| Generate Architecture | 15-25s |
| Generate Code Prototype | 20-40s |
| Generate Visual Prototype | 15-30s |
| Generate Tests | 10-20s |
| Export ZIP | 1-3s |
| Clear Workspace | <1s |

**If Slower:**
- Check internet connection (API calls)
- Check if running background jobs
- Verify RAG cache is working (Phase 2)

---

## Success Checklist

After completing all tests:

- [ ] Code Editor works perfectly
- [ ] Test Generator creates clean tests
- [ ] Export Manager creates ZIP
- [ ] Workspace cleanup deletes files
- [ ] PM Mode toggle works
- [ ] Meeting notes load in PM Mode
- [ ] NO ``` markers in ANY outputs
- [ ] Dev/PM outputs don't conflict
- [ ] Storage metrics update
- [ ] No errors in any workflow

**If all checked:** ✅ Phases 0 & 1 are COMPLETE and working!

**If issues:** 🐛 Document the issue and report

---

## Reporting Issues

**When reporting bugs, include:**

1. **What you did** (steps to reproduce)
2. **What happened** (actual behavior)
3. **What you expected** (expected behavior)
4. **Screenshots** (if relevant)
5. **Browser console errors** (F12 → Console)
6. **File contents** (if ``` markers present)

**Example Bug Report:**
```
Test: Test 2 (Test Generator)
Issue: Generated test file has ``` python at start
Steps: Generate code → Tests tab → Generate Tests
Expected: Clean Python code
Actual: File starts with ``` python
File: outputs/prototypes/test_component.py
```

---

## Next Steps After Testing

**If all tests pass:**
1. 🎉 Celebrate! Phases 0 & 1 are solid
2. 📝 Document any observations
3. 🚀 Ready for Phase 2 (Intelligent Caching)

**If tests fail:**
1. 🐛 Document the failures
2. 🔧 Fix the issues
3. 🔁 Retest
4. ✅ Verify fixes work

---

## Test 11: ULTRA-AGGRESSIVE Cache Busting (v2.5.2) 🔥

**Purpose:** Verify outputs always show latest changes instantly

**Steps:**
1. Generate a visual prototype (PM or Dev mode)
2. Go to **Interactive Editor** tab
3. Make a change via AI (e.g., "make the button blue")
4. Observe auto-save notification
5. Go to **📊 Outputs** tab
6. Look for "🔄 New version detected, reloading..." message
7. Verify the change appears (button should be blue)
8. Return to Interactive Editor
9. Make another change (e.g., "add a header")
10. Go to Outputs tab again
11. Verify new change appears immediately

**Expected Results:**
- ✅ Auto-save happens after AI modification
- ✅ "🔄 New version detected" message appears in Outputs
- ✅ Changes appear instantly (no manual refresh needed)
- ✅ Multiple modifications all show up correctly
- ✅ No stale/cached content served

**If Issues:**
- Check file modification time in `outputs/prototypes/`
- Verify no duplicate `architect_ai_cursor_poc/architect_ai_cursor_poc/` folder exists
- Check browser console for errors

---

## Test 12: Continuous Version Flow (v2.5.2) 🔄

**Purpose:** Verify version history restoration flows to Outputs seamlessly

**Steps:**
1. Go to **Interactive Editor** with an existing prototype
2. Make 3-4 changes via AI to create version history
3. Open **📜 Version History** expander (in preview panel)
4. Click **👁️ View** on an old version
5. Observe "📖 Viewing version X" message
6. Go to **📊 Outputs** tab
7. Verify it still shows the CURRENT version (not the one you viewed)
8. Return to Interactive Editor
9. Click **💾 Save** on the old version you viewed
10. Observe "✅ Version X restored & saved to Outputs!" + balloons
11. Go to **📊 Outputs** tab
12. Click **🔄 Force Refresh** button
13. Verify the restored version now appears

**Expected Results:**
- ✅ **👁️ View** previews without saving
- ✅ **💾 Save** restores AND saves to file
- ✅ Outputs tab shows restored version immediately
- ✅ No confusion about which version is "current"

**If Issues:**
- Check if file timestamp updated after 💾 Save
- Verify `st.rerun()` triggered after save
- Check session state for cache busters

---

## Test 13: Absolute Path Architecture & Portability (v2.5.2) 🗂️

**Purpose:** Verify tool works from any directory and is portable

**Scenario A: Run from Different Directories**

**Steps:**
1. Close the app if running
2. Open terminal in **project root** (Dawn-final-project)
3. Run: `python architect_ai_cursor_poc/launch.py`
4. Generate a prototype
5. Note the file path shown
6. Close the app
7. Navigate to `cd architect_ai_cursor_poc`
8. Run: `python launch.py`
9. Check **📊 Outputs** tab
10. Verify the previously generated prototype is still there

**Expected Results:**
- ✅ App works from both directories
- ✅ Outputs go to SAME location (architect_ai_cursor_poc/outputs/)
- ✅ No duplicate outputs folders created
- ✅ Previously generated files are accessible

**Scenario B: Verify Single Outputs Folder**

**Steps:**
1. Open File Explorer / Terminal
2. Navigate to project root
3. Search for all "outputs" folders
4. Count how many exist inside `architect_ai_cursor_poc/`

**Expected Results:**
- ✅ Only ONE outputs folder exists: `architect_ai_cursor_poc/outputs/`
- ✅ No `architect_ai_cursor_poc/architect_ai_cursor_poc/` nested folder
- ✅ All prototypes in `architect_ai_cursor_poc/outputs/prototypes/`

**If Issues:**
- Delete any `architect_ai_cursor_poc/architect_ai_cursor_poc/` folder
- Verify `_APP_ROOT = Path(__file__).parent.parent` in app_v2.py
- Check interactive_prototype_editor.py uses absolute paths

---

## Test 14: Automatic RAG Ingestion (v2.5.2) 🔄

**Purpose:** Verify automatic RAG ingestion system works correctly

**Scenario A: Auto-Ingestion Status**

**Steps:**
1. Launch the app
2. Look at **Sidebar** for "🔄 Auto-Ingestion Status" section
3. Check if auto-ingestion is enabled and running

**Expected Results:**
- ✅ Shows "🟢 Auto-ingestion is running" (if enabled)
- ✅ Displays active jobs and pending events counters
- ✅ Shows recent indexing activity
- ✅ Manual controls (pause/resume/refresh) are available

**Scenario B: File Change Detection**

**Steps:**
1. Ensure auto-ingestion is running
2. Create a new file in your repository (e.g., `test_file.py`)
3. Add some content to the file
4. Watch the sidebar for indexing activity
5. Wait 30 seconds and check status

**Expected Results:**
- ✅ File change is detected within 5 seconds
- ✅ Indexing job appears in active jobs
- ✅ File is processed and indexed automatically
- ✅ No manual intervention required

**Scenario C: Manual Refresh**

**Steps:**
1. Click "🔄 Refresh Now" button in auto-ingestion status
2. Wait for completion
3. Check for success message

**Expected Results:**
- ✅ Manual refresh triggers successfully
- ✅ Success message appears
- ✅ RAG index is updated

**If Issues:**
- Check if `watchdog` library is installed: `pip install watchdog`
- Verify `rag/config.yaml` has `auto_ingestion.enabled: true`
- Check browser console for errors
- Run diagnostic: `python start_auto_ingestion.py`

---

## Test 15: RAG Index Freshness Tracking (v2.5.2) 📊

**Purpose:** Verify RAG freshness detection and warnings

**Scenario A: Fresh Index**

**Steps:**
1. Run `python rag/ingest.py` to rebuild RAG index (or use auto-ingestion)
2. Launch the app
3. Look at **Sidebar**
4. Find RAG status section (may be in expander)

**Expected Results:**
- ✅ Shows "✅ RAG Status" or "Index is fresh"
- ✅ Displays number of indexed files
- ✅ Shows last updated timestamp

**Scenario B: Stale Index**

**Steps:**
1. Navigate to `rag/index/manifest.json`
2. Edit the `last_updated` field to 3 days ago
3. Relaunch the app
4. Check sidebar

**Expected Results:**
- ✅ Shows "⚠️ RAG index is X days old"
- ✅ Suggests running `python rag/ingest.py`
- ✅ Provides refresh instructions

**If Issues:**
- Check if `rag/refresh_manager.py` exists
- Verify `rag/index/manifest.json` exists
- Check threshold in `refresh_manager.py` (default: 24 hours)

---

## Test 16: Complete Path Synchronization (v2.5.2) 🎯

**Purpose:** Verify interactive editor and outputs tab use same file

**Steps:**
1. Generate a visual prototype
2. Note its content (e.g., button color)
3. Go to **Interactive Editor**
4. Make a specific change (e.g., "make button red")
5. Wait for auto-save
6. Open File Explorer
7. Navigate to `architect_ai_cursor_poc/outputs/prototypes/`
8. Open `pm_visual_prototype.html` (or developer_visual_prototype.html) in a text editor
9. Search for "red" or the change you made
10. Verify it's in the file
11. Go back to app → **📊 Outputs** tab
12. Inspect the displayed prototype

**Expected Results:**
- ✅ Change is in the file on disk
- ✅ Change appears in Outputs tab
- ✅ Interactive editor, file, and outputs tab ALL show same content
- ✅ Only ONE file exists (not multiple versions)

**If Issues:**
- Check if interactive_prototype_editor.py uses:
  ```python
  _MODULE_ROOT = Path(__file__).parent.parent
  outputs_dir = _MODULE_ROOT / "outputs" / "prototypes"
  ```
- Verify app_v2.py uses similar absolute path
- Delete any duplicate outputs folders

---

**Happy Testing!** 🧪

**Remember:** The goal is production-ready quality. Every bug found now is one less in production!

**v2.5.2 Testing Priority:**
1. 🔥 **Cache Busting** (Test 11) - Critical for UX
2. 🔄 **Version Flow** (Test 12) - Key workflow feature
3. 🔄 **Auto RAG Ingestion** (Test 14) - Real-time context updates
4. 🗂️ **Path Sync** (Test 16) - Foundation for everything
5. 📊 **RAG Freshness** (Test 15) - Context quality
6. 🗂️ **Portability** (Test 13) - Future-proofing

