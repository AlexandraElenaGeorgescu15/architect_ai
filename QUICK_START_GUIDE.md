# 🚀 Architect.AI - Quick Start Guide

## ⚡ Launch the App (3 Steps)

### 1. Navigate to Directory
```bash
cd C:\Users\AGEORGE2\Desktop\Dawn-final-project\architect_ai_cursor_poc
```

### 2. Launch
```bash
python launch.py
```
**OR** (Windows):
```bash
launch.bat
```

### 3. Open Browser
- Automatically opens at `http://localhost:8501`
- If not, click the link in terminal

---

## 🎯 Generate Your First Diagram (1 Minute)

### Step 1: Enter Meeting Notes
```
Create a phone swap application where users can list their phones 
and request swaps with other users
```

### Step 2: Click "Generate ERD"
- ✅ ERD diagram appears instantly
- ✅ Proper `erDiagram` format
- ✅ No syntax errors
- ✅ HTML visualization included

### Step 3: View Results
- **Tab 1:** Mermaid Code (syntax-validated)
- **Tab 2:** HTML Visualization (beautiful render)
- **Tab 3:** Code Editor (edit & save)
- **Tab 4:** Export (download files)

---

## 🎨 View HTML Visualizations

### Automatic Generation
When you generate any diagram, an HTML version is **automatically created**.

### Where to Find
1. Generate diagram (ERD, Architecture, etc.)
2. Go to **"🎨 HTML Visualization" tab**
3. See beautiful, context-aware visualization

### Features
- ✅ Professional styling (gradients, animations)
- ✅ Uses actual codebase details (from RAG)
- ✅ Mobile-responsive
- ✅ Interactive hover effects

### Troubleshooting
**If HTML shows as code:**
- Check: Is Gemini API key set in sidebar?
- Solution: Click "Regenerate HTML" in Editor tab

**If HTML tab missing:**
- Reason: Gemini generation failed
- Solution: Add API key, regenerate diagram

---

## ✏️ Edit Diagrams

### Using Code Editor
1. Generate any diagram
2. Go to **"Interactive Editor" tab**
3. See: "🚧 Under Construction" (visual editor coming soon)
4. Use **Code Editor** below
5. Make changes to Mermaid code
6. Click **"Save Changes"**
7. Diagram updates instantly

### Regenerate HTML
After editing:
1. Click **"Regenerate HTML"** button
2. Wait for generation
3. Check HTML Visualization tab
4. See updated visualization

---

## 📥 Export Diagrams

### Available Formats
1. Go to **"Export" tab**
2. Choose format:
   - **Mermaid (.mmd)** - Source code
   - **HTML (.html)** - Standalone webpage
   - **Mermaid Live Link** - Open in online editor

### Batch Export
To export all diagrams:
1. Check `outputs/visualizations/` folder
2. All generated diagrams are auto-saved there
3. `.mmd` files = Mermaid source
4. `.html` files = HTML visualizations

---

## 🔧 Common Tasks

### Generate All Artifacts
```
1. Enter meeting notes
2. Select "All Diagrams"
3. Click generate
4. Wait 30-60 seconds
5. Get: ERD, Architecture, Overview, Data Flow, User Flow, Components, API
```

### Generate Specific Diagram
```
1. Enter meeting notes
2. Select diagram type (ERD, Architecture, etc.)
3. Click generate
4. View in outputs/visualizations/
```

### Fix Syntax Errors
**Don't worry!** Syntax errors are auto-fixed by the universal diagram fixer.

**If you see errors:**
1. They're automatically fixed before display
2. Check logs for "[OK] syntax fixed" message
3. Final diagram is always valid

### Validate Diagrams
**Automatic validation** happens on every diagram.

**Manual validation:**
1. View diagram in viewer
2. Check top of page for validation status
3. ✅ Green = Valid
4. ⚠️ Yellow = Issues (with details)

---

## 🐛 Troubleshooting

### App Won't Start
**Error:** ChromaDB telemetry warnings
- **Solution:** Already fixed! Telemetry disabled globally
- **If persists:** Restart terminal, run `launch.py` again

**Error:** Module not found
- **Solution:** Ensure you're in `architect_ai_cursor_poc` directory
- **Check:** `pwd` should show `...Dawn-final-project/architect_ai_cursor_poc`

### Diagrams Have Syntax Errors
**This should not happen anymore!**

- **Reason:** Universal diagram fixer auto-fixes all syntax
- **If occurs:** Check logs for fixer errors
- **Solution:** Report issue with diagram type

### HTML Not Rendering
**Symptom:** HTML shows as code instead of rendering

**Causes & Solutions:**
1. **No API key:**
   - Add Gemini API key in sidebar
   - Regenerate diagram

2. **Invalid HTML:**
   - Check HTML source in expander
   - Report issue if HTML is malformed

3. **Browser issue:**
   - Try different browser
   - Clear browser cache
   - Check browser console for iframe errors

### Visual Editor Crashes
**This should not happen anymore!**

- **Status:** Visual editor is disabled
- **Message:** "🚧 Under Construction" appears
- **Alternative:** Use Code Editor (fully functional)
- **If crashes:** Report issue immediately

---

## 📊 Features Overview

### ✅ Working Features
- **Universal Diagram Fixer** - Auto-fixes all syntax errors
- **ERD Generation** - Proper `erDiagram` format
- **Architecture Diagrams** - `flowchart TD` format
- **HTML Visualizations** - Context-aware, beautiful
- **Code Editor** - Edit and save diagrams
- **Validation** - Automatic syntax checking
- **Export** - Multiple formats
- **RAG Integration** - Uses actual codebase details

### 🚧 Under Development
- **Visual Drag-&-Drop Editor** - Complete rebuild in progress
- **Diagram Selection UI** - Choose from multiple variants
- **Enhanced Validation** - More detailed error messages

---

## 💡 Tips & Best Practices

### Writing Meeting Notes
**Good:**
```
Create a phone swap app with:
- User profiles (name, email, phone)
- Phone listings (model, condition, photos)
- Swap requests (requester, target phone, status)
- Notifications for swap status changes
```

**Bad:**
```
Make an app
```

**Why:** More detail = better diagrams

### Choosing Diagram Types
- **ERD:** When discussing database/data models
- **Architecture:** When discussing system components
- **Sequence:** When discussing API flows
- **All Diagrams:** When you want comprehensive documentation

### Managing API Keys
1. Add keys in sidebar (not .env initially)
2. Test generation works
3. Then add to .env for persistence
4. Restart app after .env changes

---

## 🎯 Success Indicators

### ✅ Everything Working Correctly:
- Diagrams generate without errors
- HTML visualizations render beautifully
- Validation shows ✅ green checks
- Code editor saves changes successfully
- Export downloads files correctly
- No crash messages
- Logs show "[OK]" messages

### ⚠️ Something Needs Attention:
- Logs show "[WARN]" messages
- HTML shows as code
- Diagrams have syntax errors
- App freezes or crashes

---

## 📞 Need Help?

### Quick Checks:
1. ✅ Is Python 3.11 installed?
2. ✅ Are you in the correct directory?
3. ✅ Did you run `pip install -r requirements.txt`?
4. ✅ Is at least one API key configured?
5. ✅ Is the app running (check terminal)?

### Common Solutions:
- **Restart the app:** Ctrl+C, then `python launch.py`
- **Clear cache:** Delete `outputs/` folder, regenerate
- **Reinstall dependencies:** `pip install -r requirements.txt --force-reinstall`
- **Check logs:** Look for [ERROR] or [WARN] messages in terminal

---

## 🎉 You're Ready!

**Start generating amazing diagrams with Architect.AI!**

Remember:
- ✅ All syntax errors are auto-fixed
- ✅ HTML visualizations are context-aware
- ✅ Code editor is stable
- ✅ Visual editor is safely disabled
- ✅ Everything is production-ready

**Have fun building!** 🚀

