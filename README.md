# Architect.AI v3.5.2 🚀

**AI-Powered Software Architecture & Development Assistant**

Transform your requirements into production-ready artifacts in seconds using advanced RAG, Knowledge Graph, and Pattern Mining intelligence.

---

## 🎯 What is Architect.AI?

Architect.AI is a full-stack AI development assistant that generates **context-aware** software artifacts tailored to YOUR specific project. Unlike generic AI tools, Architect.AI learns your codebase, understands your architecture, and produces artifacts that actually match your tech stack and coding style.

### Key Features

- **🧠 5-Layer Intelligence System**
  - RAG (Retrieval-Augmented Generation) - Pulls relevant code from your project
  - Knowledge Graph - Maps your architecture (classes, functions, relationships)
  - Pattern Mining - Detects design patterns, code smells, security issues
  - Meeting Notes - Captures requirements and context
  - AI Analysis - Ties everything together for hyper-accurate generation

- **📊 50+ Artifact Types**
  - Diagrams: ERD, Architecture, Sequence, Class, State, Flowchart, C4, UML
  - Code: Full prototypes with tests (React, Angular, Vue, Python, Node.js, etc.)
  - Documentation: API docs, Jira tasks, user stories, personas, workflows
  - Project Management: Backlog, estimations, feature scoring

- **🎨 Modern React + FastAPI Stack**
  - React 18 + TypeScript frontend with Tailwind CSS
  - FastAPI Python backend with async/await
  - Real-time WebSocket updates
  - Premium dark/light mode UI

- **🤖 Multi-Model Support**
  - **Local**: Ollama (DeepSeek, Llama, Mistral, CodeLlama, Qwen)
  - **Cloud**: Google Gemini, OpenAI GPT-4, Groq, Anthropic Claude
  - Smart model routing per artifact type
  - Local fine-tuning with LoRA/QLoRA

- **🔄 Continuous Learning**
  - Feedback system (thumbs up/down) trains models
  - Adaptive learning from your preferences
  - Synthetic dataset generation for bootstrapping
  - Automatic quality validation and retry

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ (3.11 recommended)
- Node.js 18+ (for frontend)
- Ollama (optional, for local models)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd architect_ai_cursor_poc
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Set up API keys (optional)**
   ```bash
   # Copy the example .env file
   cp .env.example .env
   
   # Edit .env and add your API keys:
   # GEMINI_API_KEY=your_gemini_key_here
   # OPENAI_API_KEY=your_openai_key_here
   # GROQ_API_KEY=your_groq_key_here
   # ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

5. **Launch the application**
   ```bash
   # Option 1: Use the launcher script (recommended)
   python launch.py
   
   # Option 2: Windows batch file
   launch.bat
   
   # Option 3: Linux/Mac shell script
   ./launch.sh
   ```

6. **Open your browser**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

---

## 📖 User Guide

### 1. Add Your Project

Place your project files in one of these locations:
- `agents/` - AI agent code
- `components/` - Reusable components
- `final_project/` - Your main project
- `final-proj-sln/` - Alternative project location

Or configure custom directories in `backend/core/config.py` under `USER_PROJECT_DIRECTORIES`.

### 2. Index Your Project

The RAG system automatically indexes your project on startup:
- Watches for file changes in real-time
- Builds Knowledge Graph and Pattern Mining analysis
- Creates embeddings for semantic search

**Manual reindex:**
```bash
cd architect_ai_cursor_poc
python -m rag.ingest
```

### 3. Add Meeting Notes

1. Click the **Meeting Notes** panel (left side)
2. Type requirements or upload files (.txt, .md, .pdf)
3. AI automatically suggests folders to organize notes
4. Notes are used as context for artifact generation

### 4. Generate Artifacts

1. Click **Build Context** to activate the 5-layer intelligence
2. Select artifact type from the dropdown
3. Click **Generate** and wait 10-30 seconds
4. View, edit, download, or provide feedback

### 5. Iterate & Improve

- Use **Ask AI** for quick questions about your codebase
- Provide feedback (👍/👎) to train the models
- Visit **Intelligence** page to see Knowledge Graph, Pattern Mining, and training data
- Fine-tune local models with your feedback data

---

## 🏗️ Architecture

### Directory Structure

```
architect_ai_cursor_poc/
├── backend/                  # FastAPI backend
│   ├── api/                  # API endpoints
│   ├── core/                 # Config, database, middleware
│   ├── services/             # Business logic
│   ├── models/               # Database models
│   └── main.py               # Entry point
├── frontend/                 # React + TypeScript frontend
│   └── src/
│       ├── components/       # React components
│       ├── pages/            # Main pages (Studio, Intelligence, Canvas)
│       ├── services/         # API clients
│       └── stores/           # Zustand state management
├── components/               # Python AI components
│   ├── knowledge_graph.py    # AST parsing + NetworkX
│   ├── pattern_mining.py     # Static analysis
│   ├── local_finetuning.py   # LoRA/QLoRA training
│   └── _tool_detector.py     # Self-contamination prevention
├── rag/                      # RAG system (ChromaDB)
│   ├── ingest.py             # Indexing
│   ├── retrieve.py           # Hybrid search
│   └── config.yaml           # Exclusion rules
├── validation/               # Quality assurance
│   └── output_validator.py   # 8 validators, scoring
├── workers/                  # Background tasks
│   └── finetuning_worker.py  # Ollama auto-training
├── data/                     # SQLite database, meeting notes
├── outputs/                  # Generated artifacts
├── documentation/            # API docs, architecture
└── tests/                    # Test suite
```

### Technology Stack

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy (ORM)
- ChromaDB (vector database)
- NetworkX (knowledge graph)
- HuggingFace Transformers (fine-tuning)
- Ollama (local LLM serving)

**Frontend:**
- React 18 + TypeScript
- Tailwind CSS (styling)
- Zustand (state management)
- Axios (HTTP client)
- Monaco Editor (code editing)
- Mermaid.js (diagram rendering)

**AI/ML:**
- Google Gemini API
- OpenAI GPT-4 API
- Groq API (Llama models)
- Anthropic Claude API
- Sentence Transformers (embeddings)
- LoRA/QLoRA (parameter-efficient fine-tuning)

---

## 🔧 Configuration

### API Keys

Edit `.env` file in project root:

```bash
# Google Gemini (recommended for primary model)
GEMINI_API_KEY=your_gemini_api_key_here

# OpenAI (GPT-4, GPT-3.5)
OPENAI_API_KEY=your_openai_api_key_here

# Groq (fast Llama inference)
GROQ_API_KEY=your_groq_api_key_here

# Anthropic (Claude models)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# X.AI (Grok models) - alternative to Groq
XAI_API_KEY=your_xai_api_key_here
```

### Model Routing

Configure which model to use for each artifact type in **Intelligence > Model Mapping**.

**Default routing:**
- ERDs: `deepseek-coder:6.7b` (local) → Gemini (fallback)
- Architecture: `deepseek-coder:6.7b` (local) → Gemini (fallback)
- Code: `deepseek-coder:6.7b` (local) → GPT-4 (fallback)
- Diagrams: `deepseek-coder:6.7b` (local) → Gemini (fallback)

### RAG Configuration

Edit `rag/config.yaml` to exclude files/directories from indexing:

```yaml
ignore_globs:
  - "node_modules/**"
  - "venv/**"
  - "*.min.js"
  - "dist/**"
  - "build/**"
```

---

## 🧪 Testing

Run the comprehensive test suite:

```bash
# All tests
python tests/test_comprehensive_coverage.py

# Specific test
python -m pytest tests/test_knowledge_graph.py -v

# With coverage
python -m pytest tests/ --cov=components --cov-report=html
```

**Critical tests:**
- `test_tool_detector.py` - Self-contamination prevention
- `test_ollama_vram.py` - VRAM management
- `test_knowledge_graph.py` - AST parsing
- `test_pattern_mining.py` - Static analysis

---

## 📊 Performance

**Typical Generation Times:**
- ERD: 10-15 seconds
- Architecture diagram: 15-20 seconds
- Code prototype: 20-30 seconds
- API documentation: 10-15 seconds

**Scalability:**
- Handles codebases up to 100,000+ files
- Incremental indexing for fast updates
- Parallel artifact generation
- Lazy loading for fast startup

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.10+

# Install missing dependencies
pip install -r requirements.txt

# Check for port conflicts
netstat -ano | findstr :8000
```

### Frontend won't start
```bash
cd frontend
npm install  # Reinstall dependencies
npm run dev  # Should open on port 3000
```

### RAG index not building
```bash
# Check user project directories
python check_api_keys.py

# Manual reindex
python -m rag.ingest
```

### Ollama models not appearing
```bash
# Check Ollama is running
ollama list

# Pull a model
ollama pull deepseek-coder:6.7b-instruct-q4_K_M
```

See `frontend/TROUBLESHOOTING.md` for more details.

---

## 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - 5-minute getting started guide
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history and changes
- **[API_KEYS_SETUP.md](./API_KEYS_SETUP.md)** - Detailed API key configuration
- **[documentation/API.md](./documentation/API.md)** - Full API reference
- **[documentation/ARCHITECTURE.md](./documentation/ARCHITECTURE.md)** - Technical deep dive
- **[documentation/WEBSOCKET_API.md](./documentation/WEBSOCKET_API.md)** - WebSocket protocol

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Code Quality**: Use type hints, docstrings, and follow PEP 8
2. **Testing**: Add tests for new features (80%+ coverage)
3. **Documentation**: Update README and CHANGELOG
4. **No Self-Contamination**: Never index tool's own code

See `.cursorrules` for detailed development standards.

---

## 📝 License

[Specify your license here]

---

## 🙏 Acknowledgments

- **Ollama** - Local LLM serving
- **HuggingFace** - Model fine-tuning infrastructure
- **Google Gemini** - High-quality model API
- **OpenAI** - GPT-4 and GPT-3.5 models
- **ChromaDB** - Vector database for RAG
- **FastAPI** - Modern Python web framework
- **React** - Frontend UI framework

---

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: See `documentation/` folder
- **Troubleshooting**: See `frontend/TROUBLESHOOTING.md`

---

**Built with ❤️ by the Architect.AI team**

*Version 3.5.2 - November 2025*

