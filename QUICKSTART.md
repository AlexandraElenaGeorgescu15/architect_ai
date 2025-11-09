# 🚀 Architect.AI - Quick Start Guide

**Get up and running in 5 minutes!**

---

## Prerequisites

- **Python 3.9+** installed
- **Git** (to clone the repository)
- **Ollama** (recommended) or Cloud AI API keys (Groq, OpenAI, or Gemini)

---

## Step 1: Clone & Install (2 minutes)

```bash
# Clone repository
git clone <repository-url>
cd architect_ai_cursor_poc

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure AI Provider (1 minute)

**Option A: Use Ollama (Recommended - Free & Local)**

```bash
# Install Ollama
# Visit: https://ollama.com/download

# Download a model (3-8GB)
ollama pull llama3.2:3b

# Verify it's running
ollama list
```

**Option B: Use Cloud AI (Requires API Key)**

Create `.env` file:
```bash
# Choose ONE provider:
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
# OR
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
# OR
GEMINI_API_KEY=xxxxxxxxxxxxx
```

Get API keys:
- **Groq:** https://console.groq.com/keys (Free tier available)
- **OpenAI:** https://platform.openai.com/api-keys (Paid)
- **Gemini:** https://makersuite.google.com/app/apikey (Free tier available)

---

## Step 3: Prepare Your Codebase (30 seconds)

Place your project code in a sibling directory:

```
Dawn-final-project/
├── architect_ai_cursor_poc/  ← The AI tool
├── your-project/             ← Your code goes here
└── another-project/          ← Or here
```

**Note:** The tool automatically excludes itself and only analyzes your project directories.

---

## Step 4: Launch the App (30 seconds)

```bash
# From architect_ai_cursor_poc directory
python launch.py

# Or directly:
streamlit run app/app_v2.py
```

The app will open in your browser at `http://localhost:8501`

---

## Step 5: Generate Your First Artifact (1 minute)

1. **Upload Meeting Notes**
   - Go to the "📝 Meeting Notes" section
   - Enter your feature requirements (minimum 80 characters)
   - Example: "Create a user authentication system with login, registration, password reset, and JWT tokens"

2. **Generate Artifacts**
   - Scroll down to "Artifact Generation"
   - Click **"Generate ERD"** (fastest, 10-20 seconds)
   - View your Entity-Relationship Diagram!

3. **Explore More Artifacts**
   - **Architecture Diagram:** System component relationships
   - **API Documentation:** Endpoint specifications
   - **Code:** Actual implementation
   - **JIRA Tasks:** Story points and subtasks
   - **Visual Prototype:** HTML/Angular/React prototype

---

## What Just Happened?

Architect.AI analyzed YOUR codebase and used:

1. **RAG (Retrieval-Augmented Generation):** Retrieved relevant code snippets from YOUR repository
2. **Knowledge Graph:** Mapped YOUR component relationships using AST parsing
3. **Pattern Mining:** Detected YOUR design patterns (Singleton, Factory, Observer)
4. **5-Layer Context:** Combined meeting notes + RAG + analysis + KG + patterns
5. **Validation:** Checked artifact quality (Mermaid syntax, 0-100 score, auto-retry)

**Result:** Production-ready artifacts that understand YOUR architecture, not generic templates!

---

## Verification Checklist

Run the verification script:

```bash
python tests/run_tests.py
```

Expected output:
```
[TEST 1/5] Critical imports ................... [PASS]
[TEST 2/5] ChromaDB connection ................ [PASS]
[TEST 3/5] AI agent initialization ............ [PASS]
[TEST 4/5] Validation system .................. [PASS]
[TEST 5/5] File system ........................ [PASS]

RESULTS: 5/5 tests passed
```

---

## Troubleshooting

### "Ollama not running"
```bash
# Start Ollama service
ollama serve

# In another terminal, verify
ollama list
```

### "No API key configured"
- Check your `.env` file exists
- Ensure key starts with correct prefix (gsk_/sk_/AIza)
- Restart the app after adding keys

### "Meeting notes too short"
- Minimum 80 characters required
- Add more context: feature description, technical requirements, use cases

### "No RAG results"
- Ensure your project code is in a sibling directory (not inside `architect_ai_cursor_poc/`)
- Check `rag/index/` exists and has data
- Run manual indexing: `python -m rag.ingest`

### "Import errors"
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check Python version
python --version  # Must be 3.9+
```

---

## Next Steps

### Explore Advanced Features

1. **Fine-Tuning (Adaptive Learning)**
   - Go to "🎓 Fine-Tuning" tab
   - Add feedback when AI makes mistakes
   - System learns from corrections

2. **Knowledge Graph Visualization**
   - Go to "🧠 Knowledge Graph" section
   - View YOUR component relationships as a graph
   - See coupling metrics, complexity scores

3. **Pattern Mining Analysis**
   - Go to "🔍 Pattern Mining" section
   - See YOUR design patterns detected
   - Get code quality recommendations

4. **Batch Generation**
   - Generate all 8+ artifacts at once
   - Click "Generate All Artifacts"
   - Takes 2-5 minutes depending on AI provider

### Read Full Documentation

- **README.md** - Complete feature list and architecture
- **TECHNICAL_DOCUMENTATION.md** - Deep dive into systems
- **FINETUNING_GUIDE.md** - Complete fine-tuning workflow
- **TROUBLESHOOTING.md** - Common issues and solutions

---

## Quick Tips

💡 **Tip 1:** Use Ollama for fast, free local generation (works offline!)  
💡 **Tip 2:** Use Groq (cloud) for fastest generation (0.5-2 seconds per artifact)  
💡 **Tip 3:** Use GPT-4/Claude for highest quality (but slower and paid)  
💡 **Tip 4:** Enable "Enhanced RAG" for better context (100 chunks vs 18)  
💡 **Tip 5:** Add feedback to fine-tune the AI to your coding style

---

## Support

- **GitHub Issues:** Report bugs or request features
- **Documentation:** Read `README.md` and `TECHNICAL_DOCUMENTATION.md`
- **Tests:** Run `python tests/run_tests.py` to verify setup

---

## Success! 🎉

You're now ready to transform meeting notes into production-ready artifacts that understand YOUR codebase!

**Happy architecting!** 🏗️

