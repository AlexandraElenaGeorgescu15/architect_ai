# Architect.AI - Quick Start Guide ⚡

Get up and running with Architect.AI in 5 minutes!

---

## Prerequisites ✅

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+** 
- **Git**
- **Ollama** (optional, for local models) - [Download here](https://ollama.ai)

---

## Step 1: Install Dependencies (2 minutes)

### Backend (Python)
```bash
cd architect_ai_cursor_poc
pip install -r requirements.txt
```

### Frontend (Node.js)
```bash
cd frontend
npm install
cd ..
```

---

## Step 2: Configure API Keys (1 minute) - OPTIONAL

Create a `.env` file in `architect_ai_cursor_poc/`:

```bash
# Google Gemini (recommended - free tier available)
GEMINI_API_KEY=your_gemini_api_key_here

# OpenAI (optional)
OPENAI_API_KEY=your_openai_api_key_here

# Groq (optional - fast Llama inference)
GROQ_API_KEY=your_groq_api_key_here

# Anthropic Claude (optional)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Get API Keys:**
- **Gemini**: https://ai.google.dev/ (Free tier: 60 requests/minute)
- **OpenAI**: https://platform.openai.com/api-keys
- **Groq**: https://console.groq.com/
- **Anthropic**: https://console.anthropic.com/

**Note:** You can use Architect.AI with just local Ollama models (no API keys needed), but cloud models provide better quality.

---

## Step 3: Install Local Models (1 minute) - OPTIONAL

If you want to use local models (free, private, no API keys):

```bash
# Install Ollama from https://ollama.ai

# Pull recommended models
ollama pull deepseek-coder:6.7b-instruct-q4_K_M
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
ollama pull mistral-nemo:12b-instruct-2407-q4_K_M
```

---

## Step 4: Launch Architect.AI (30 seconds)

### Option 1: Launcher Script (Recommended)
```bash
python launch.py
```

### Option 2: Windows
```bash
launch.bat
```

### Option 3: Linux/Mac
```bash
chmod +x launch.sh
./launch.sh
```

The launcher will:
1. Start the FastAPI backend on http://localhost:8000
2. Start the React frontend on http://localhost:3000
3. Auto-index your project files
4. Build Knowledge Graph and Pattern Mining
5. Open your browser automatically

---

## Step 5: Generate Your First Artifact (1 minute)

1. **Add Meeting Notes** (left panel)
   - Type: "Create a user authentication system with login, signup, and password reset"
   - Or upload a requirements file (.txt, .md, .pdf)

2. **Build Context** (center panel)
   - Click the "Build Context" button
   - Wait 5-10 seconds for RAG, Knowledge Graph, and Pattern Mining to activate

3. **Generate Artifact**
   - Select artifact type: "ERD (Entity-Relationship Diagram)"
   - Click "Generate"
   - Wait 10-15 seconds

4. **View Result** (right panel - Outputs)
   - Click the generated artifact to open viewer
   - Preview the Mermaid diagram
   - Provide feedback (👍/👎)
   - Download or export

---

## 🎉 You're Done!

### Next Steps:

1. **Add Your Project**
   - Place your project files in: `agents/`, `components/`, `final_project/`, or `final-proj-sln/`
   - Restart the app to auto-index your codebase

2. **Explore Artifact Types**
   - Try: Architecture Diagram, Sequence Diagram, Code Prototype, API Docs, Jira Tasks

3. **Visit Intelligence Page**
   - View Knowledge Graph (your architecture map)
   - See Pattern Mining results (design patterns, code smells)
   - Configure model routing
   - Check training data

4. **Fine-Tune Models**
   - Provide feedback on generated artifacts (👍/👎)
   - After 50+ examples, fine-tune local models
   - Models learn your coding style and architecture

---

## 🆘 Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Check port 8000 is free
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Linux/Mac
```

### Frontend won't start
```bash
cd frontend
npm install
npm run dev  # Should open on http://localhost:3000
```

### No models appearing
```bash
# Check Ollama is running
ollama list

# Pull a model
ollama pull deepseek-coder:6.7b-instruct-q4_K_M

# Verify API keys
python check_api_keys.py
```

### RAG index not building
```bash
# Check user project directories exist
ls agents/ components/ final_project/ final-proj-sln/

# Manual reindex
python -m rag.ingest
```

### Permission errors on Windows
```bash
# Run PowerShell as Administrator
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📚 Learn More

- **Full Documentation**: [README.md](./README.md)
- **API Reference**: [documentation/API.md](./documentation/API.md)
- **Architecture Guide**: [documentation/ARCHITECTURE.md](./documentation/ARCHITECTURE.md)
- **Changelog**: [CHANGELOG.md](./CHANGELOG.md)
- **API Keys Setup**: [API_KEYS_SETUP.md](./API_KEYS_SETUP.md)

---

## 🎓 Tutorial Video

Check out our interactive onboarding tour when you first open the app - it walks you through all the key features!

You can replay it anytime by clicking **"🎓 Replay Onboarding"** at the bottom of the sidebar.

---

## 💡 Pro Tips

1. **Use Build Context**: Always click "Build Context" before generating artifacts for best quality
2. **Provide Feedback**: Thumbs up/down helps the AI learn your preferences
3. **Organize Notes**: Create folders for different features/modules in Meeting Notes
4. **Try Different Models**: Some artifact types work better with specific models
5. **Fine-Tune Locally**: After 50+ feedback examples, fine-tune Ollama models for personalized results
6. **Keyboard Shortcuts**: Check the sidebar for useful shortcuts

---

## 🚀 What Can I Build?

With Architect.AI, you can generate:

- **Diagrams**: ERD, Architecture, Sequence, Class, State, Flowchart, C4, UML, Data Flow, Git Graph
- **Code**: Full React/Angular/Vue/Python prototypes with tests
- **Documentation**: API docs, system overviews, technical specs
- **Project Management**: Jira tasks, backlog, user stories, estimations, feature scoring
- **UX**: User personas, journey maps, workflows

All tailored to YOUR specific codebase and requirements!

---

**Need help? Check the [troubleshooting guide](./frontend/TROUBLESHOOTING.md) or open an issue on GitHub.**

**Happy building! 🎉**

*Last updated: November 24, 2025*

