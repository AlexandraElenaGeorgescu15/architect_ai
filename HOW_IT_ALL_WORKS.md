# 🎯 How Architect.AI Actually Works - The Complete Picture

## TL;DR - The 30-Second Version

1. **You** provide requirements (meeting notes)
2. **Universal Context** loads your entire project knowledge (baseline)
3. **RAG** retrieves targeted snippets (smart search)
4. **Context Builder** combines everything into one mega-context
5. **Model Pipeline** tries Ollama → Cloud → returns best result
6. **Validator** scores quality (0-100), retries if < 60
7. **You** get a high-quality artifact that knows YOUR project

---

## 🔄 The Complete Flow (Step-by-Step)

### **Phase 1: Startup (The Foundation)**

```
User runs: python launch.py
     ↓
Backend starts (main.py) → FastAPI server on port 8000
     ↓
┌────────────────────────────────────────────────────────┐
│ 1. Database Init (SQLite - stores jobs, feedback)      │
│ 2. Model Service Init (loads 24 models from registry)  │
│ 3. RAG Ingestion (indexes ALL your project files)      │
│ 4. Knowledge Graph (parses Python/C#/TypeScript)       │
│ 5. Pattern Mining (detects design patterns)            │
│ 6. 🚀 Universal Context Build (combines everything!)   │
└────────────────────────────────────────────────────────┘
     ↓
✅ SERVER READY - Your entire project is now indexed and known by heart!
```

**What's Happening:**
- **RAG Ingestion**: Scans every `.py`, `.cs`, `.ts`, `.tsx`, `.js`, `.jsx` file in your project
  - Excludes: `architect_ai_cursor_poc/`, `node_modules/`, `.git/`, `__pycache__/`
  - Creates embeddings (vector representations) for semantic search
  - Stores in ChromaDB at `data/rag_index/`
  
- **Knowledge Graph**: 
  - Parses code using AST (Abstract Syntax Trees)
  - Extracts: classes, functions, imports, relationships
  - Builds NetworkX graph: `User -> has -> Session`, `AuthService -> uses -> UserModel`
  
- **Pattern Mining**:
  - Detects: Singleton, Factory, Observer, MVC patterns
  - Identifies anti-patterns and code smells
  - Provides architectural insights
  
- **Universal Context**:
  - **Importance scores** every file (main workflow = 1.0, tests = 0.3)
  - Combines RAG + KG + PM into one mega-context
  - Caches for 6 hours (fast retrieval)
  - **This is the powerhouse that makes everything intelligent!**

---

### **Phase 2: User Generates an Artifact**

```
User in Frontend (Canvas page)
     ↓
Types meeting notes: "Create user authentication system"
     ↓
Selects artifact type: "mermaid_erd" (Entity-Relationship Diagram)
     ↓
Clicks "Generate" button
     ↓
frontend/src/hooks/useGeneration.ts → generate()
     ↓
POST /api/generation/artifacts
     {
       meeting_notes: "Create user authentication system",
       artifact_type: "mermaid_erd",
       context_id: null,  // Will build fresh context
       options: { max_retries: 3, use_validation: true }
     }
```

**Backend Receives Request** → `backend/api/generation.py`

---

### **Phase 3: Context Building (The Intelligence)**

```
EnhancedGenerationService.generate_with_pipeline()
     ↓
🚀 STEP 1: Get Universal Context (instant from cache)
     ├─ Total files: 1250
     ├─ Key entities: [UserModel, AuthService, SessionManager, ...]
     ├─ KG nodes: 450
     └─ Patterns: [Singleton(AuthService), Factory(TokenFactory), ...]
     
     ↓
     
🎯 STEP 2: Build Targeted Context (query-specific)
     ├─ Query expansion: "authentication, auth, user, login, session, token"
     ├─ RAG hybrid search:
     │   ├─ Vector search (semantic similarity)
     │   ├─ BM25 search (keyword matching)
     │   └─ RRF reranking (combines both)
     ├─ Artifact-type filtering: "ERD" → prioritize models, entities, schemas
     └─ Importance weighting: 
         - AuthService.cs (0.9) × relevance (0.85) = 0.88 combined score
         - Button.tsx (0.4) × relevance (0.60) = 0.52 combined score
         → AuthService wins!
     
     ↓
     
📄 STEP 3: Assemble Final Context
     ┌──────────────────────────────────────────────────────┐
     │ === UNIVERSAL PROJECT CONTEXT ===                    │
     │ Project: YourAwesomeApp                              │
     │ Files: 1250, Entities: 50, Patterns: 23              │
     │                                                       │
     │ Key Entities:                                        │
     │   - UserModel (class) - models/User.py              │
     │   - AuthService (class) - services/AuthService.cs   │
     │   - SessionManager (class) - managers/Session.ts    │
     │                                                       │
     │ === YOUR REQUIREMENTS ===                            │
     │ Create user authentication system                    │
     │                                                       │
     │ === RELEVANT CODE SNIPPETS (ranked) ===              │
     │                                                       │
     │ --- Snippet 1 ⭐⭐⭐⭐⭐ (score: 0.88) ---              │
     │ File: services/AuthService.cs                        │
     │ public class AuthService {                           │
     │   private IUserRepository _userRepo;                 │
     │   public async Task<Token> Authenticate(...) {...}   │
     │ }                                                    │
     │                                                       │
     │ --- Snippet 2 ⭐⭐⭐⭐ (score: 0.85) ---                │
     │ File: models/UserModel.py                            │
     │ class UserModel(Base):                               │
     │   __tablename__ = 'users'                            │
     │   id = Column(Integer, primary_key=True)             │
     │   email = Column(String(255), unique=True)           │
     │   password_hash = Column(String(255))                │
     │ ...                                                  │
     └──────────────────────────────────────────────────────┘
```

**Context is now ready** - 18+ code snippets + universal baseline + KG insights + pattern analysis!

---

### **Phase 4: Model Pipeline (The Generation)**

```
EnhancedGenerationService with assembled context
     ↓
🎯 Get Model Routing for "mermaid_erd"
     From model_routing.yaml:
     ├─ Primary: deepseek-coder:6.7b (Ollama)
     ├─ Fallback 1: qwen2.5-coder:7b (Ollama)
     └─ Fallback 2: Gemini 2.0 Flash (Cloud)
     
     ↓
     
📍 PHASE 1: Try Local Models (Ollama)
     
     ┌─────────────────────────────────────────────────┐
     │ Attempt 1: deepseek-coder:6.7b                  │
     ├─────────────────────────────────────────────────┤
     │ POST http://localhost:11434/api/generate        │
     │ {                                                │
     │   model: "deepseek-coder:6.7b-instruct-q4_K_M", │
     │   prompt: [assembled context + instructions],   │
     │   stream: false                                  │
     │ }                                                │
     │                                                  │
     │ Response: "erDiagram\n  USER {...}"              │
     │                                                  │
     │ ✅ Validation Score: 75/100                      │
     │    ✅ Correct syntax                             │
     │    ✅ Has entities (USER, SESSION, ROLE)         │
     │    ⚠️ Missing some relationships                 │
     │                                                  │
     │ Decision: ACCEPT (score ≥ 60)                    │
     └─────────────────────────────────────────────────┘
     
     ✅ SUCCESS - Return artifact!
     
     (If score < 60, would try qwen2.5-coder, then Gemini)
```

**Model Pipeline Logic:**
1. **Try Local First** (fast, free, private)
   - Loop through Ollama models: `deepseek-coder` → `qwen2.5-coder` → `codellama`
   - Each model gets 2 retries (3 total attempts)
   - If validation score ≥ 60 → **SUCCESS, return immediately**
   
2. **Cloud Fallback** (if all local failed)
   - Try Gemini → GPT-4 → Claude (in order)
   - More expensive but higher quality
   - Same validation: score ≥ 60 → SUCCESS
   
3. **Best Effort** (if everything failed)
   - Return the highest-scoring attempt
   - Even if score < 60, user gets something to work with
   - Include validation feedback for manual fixing

---

### **Phase 5: Validation (The Quality Check)**

```
ArtifactValidator.validate_artifact()
     ↓
Run 8 validators in parallel:
     
     ✅ 1. Syntax Validator (15 points)
         - Mermaid syntax correct?
         - No parse errors?
         
     ✅ 2. Completeness Validator (20 points)
         - Has all required elements?
         - ERD: entities, attributes, relationships
         
     ✅ 3. Semantic Validator (25 points)
         - Makes logical sense?
         - USER has email, password fields
         
     ✅ 4. Context Alignment Validator (20 points)
         - Matches user requirements?
         - "authentication system" → has USER, SESSION entities
         
     ✅ 5. Best Practices Validator (10 points)
         - Follows naming conventions?
         - Has primary keys, foreign keys?
         
     ✅ 6. Security Validator (5 points)
         - No passwords in plain text?
         - Has secure patterns?
         
     ✅ 7. Consistency Validator (3 points)
         - Naming consistent (camelCase vs snake_case)?
         
     ✅ 8. Formatting Validator (2 points)
         - Proper indentation?
         - Readable structure?
     
     ↓
     
Total Score: 75/100
     
     ├─ Syntax: 15/15 ✅
     ├─ Completeness: 18/20 ⚠️ (missing cascade deletes)
     ├─ Semantic: 23/25 ✅
     ├─ Context Alignment: 19/20 ✅
     └─ ...
     
Decision: PASS (≥ 60) ✅
```

**Validation Thresholds:**
- **≥ 90**: Excellent (celebrate! 🎉)
- **≥ 75**: Good (use as-is)
- **≥ 60**: Acceptable (minor tweaks)
- **< 60**: Needs retry (regenerate with different model)

---

### **Phase 6: Return to Frontend**

```
Backend returns response:
     {
       job_id: "gen_abc123",
       status: "completed",
       artifact: {
         id: "artifact_xyz789",
         type: "mermaid_erd",
         content: "erDiagram\n  USER {...}",
         validation_score: 75,
         metadata: {
           model_used: "deepseek-coder:6.7b",
           generation_time: 4.2,
           context_sources: ["universal_context", "rag", "kg"]
         }
       }
     }
     
     ↓
     
frontend/src/hooks/useGeneration.ts receives response
     ↓
     
Stores in Zustand: useArtifactStore.addArtifact()
     ↓
     
Shows notification: "Artifact generated successfully! 🎉"
     ↓
     
Canvas page auto-loads the diagram
     ↓
     
EnhancedDiagramEditor parses Mermaid → ReactFlow nodes
     ↓
     
User sees visual diagram! 🎨
```

---

## 🤖 The Model Pipeline in Detail

### **Ollama (Local Models)**

**What is Ollama?**
- Runs AI models **locally on your machine**
- Fast (GPU-accelerated), free, private
- Models stored in: `C:\Users\[You]\.ollama\models\`

**Available Models:**
- `deepseek-coder:6.7b` - Best for code/diagrams (6.7B parameters)
- `qwen2.5-coder:7b` - Good for technical tasks (7B parameters)
- `codellama:7b` - Meta's code model (7B parameters)
- `mistral:7b` - General purpose (7B parameters)

**How to Check:**
```powershell
ollama list
# Shows all downloaded models

ollama run deepseek-coder "Hello"
# Tests if model works
```

**VRAM Requirements:**
- 4-bit quantized (q4_K_M): ~4-6 GB VRAM
- 8-bit: ~8-10 GB VRAM
- RTX 3060 (12GB): Can run 7B models smoothly
- RTX 4090 (24GB): Can run 13B+ models

---

### **Cloud Models (Fallback)**

**When are they used?**
- All Ollama models failed (score < 60)
- Ollama not running
- Complex artifacts needing higher intelligence

**Available Providers:**
1. **Gemini (Google)** - Fast, good quality, free tier
   - API Key: In Studio → Settings → API Keys
   - Models: Gemini 2.0 Flash, Gemini 1.5 Pro
   
2. **GPT-4 (OpenAI)** - Highest quality, expensive
   - API Key: In Studio → Settings → API Keys
   - Models: GPT-4 Turbo, GPT-4, GPT-3.5
   
3. **Claude (Anthropic)** - Good for complex reasoning
   - API Key: In Studio → Settings → API Keys
   - Models: Claude 3.5 Sonnet, Claude 3 Opus

4. **Groq (X.AI)** - Fast inference, good quality
   - API Key: `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`
   - Models: Llama 3.3 70B, Llama 3.1 70B

**Cost (rough estimates):**
- Ollama: **FREE** (local)
- Gemini: **$0.10 - $0.50** per 1M tokens (has free tier)
- GPT-4: **$10 - $30** per 1M tokens
- Claude: **$15 - $75** per 1M tokens
- Groq: **$0.70 - $1.00** per 1M tokens

**Recommendation:** Use Ollama for 90% of tasks, cloud for complex edge cases.

---

### **HuggingFace Integration**

**What is it for?**
- Download new models directly from HuggingFace Hub
- Convert to Ollama format
- Fine-tune models on your project data

**How to use:**
1. Go to Intelligence page → "Search & Download Models"
2. Search: "codellama" or "mistral"
3. Click "Download" → Downloads from HuggingFace
4. Converts to Ollama format automatically
5. Now available in model list!

**Current Status:**
- ✅ Model search working
- ✅ Download working
- ⚠️ Fine-tuning: Partially implemented (needs more testing)
- 🚧 LoRA adapters: In progress

---

## 📊 The Data Flow (Visual)

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR PROJECT FILES                       │
│  (Python, C#, TypeScript, JavaScript, models, controllers)  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                              │
        ▼                              ▼
┌──────────────┐              ┌──────────────┐
│  RAG Ingestion│              │ Knowledge    │
│  (ChromaDB)   │              │ Graph (AST)  │
│  - Embeddings │              │ - Classes    │
│  - Chunks     │              │ - Functions  │
│  - Metadata   │              │ - Imports    │
└───────┬──────┘              └───────┬──────┘
        │                              │
        │         ┌────────────────────┘
        │         │      
        ▼         ▼
┌──────────────────────────┐
│  🚀 UNIVERSAL CONTEXT    │
│  (Powerhouse)            │
│  - Importance Scores     │
│  - Project Map           │
│  - Key Entities          │
│  - Pattern Analysis      │
└──────────┬───────────────┘
           │
           │  User Query: "Create auth system"
           ▼
┌──────────────────────────┐
│  Context Builder         │
│  - Universal baseline    │
│  + Targeted RAG (18)     │
│  + KG insights           │
│  + Pattern Mining        │
└──────────┬───────────────┘
           │
           │  Mega-Context (10,000+ tokens)
           ▼
┌──────────────────────────┐
│  Model Pipeline          │
│  1. Ollama (local)       │
│  2. Cloud (fallback)     │
│  3. Best effort          │
└──────────┬───────────────┘
           │
           │  Generated Artifact
           ▼
┌──────────────────────────┐
│  Validator (8 checks)    │
│  Score: 0-100            │
│  Retry if < 60           │
└──────────┬───────────────┘
           │
           │  Final Artifact (75/100)
           ▼
┌──────────────────────────┐
│  Frontend Display        │
│  - Canvas (visual)       │
│  - Code editor (text)    │
│  - Validation feedback   │
└──────────────────────────┘
```

---

## 🎓 Common Workflows

### **Workflow 1: Generate ERD from Scratch**

1. **Open Canvas** (`http://localhost:3000/canvas`)
2. **Click "Context"** tab
3. **Paste requirements:**
   ```
   Create a user management system with:
   - Users (email, password, role)
   - Sessions (token, expiry)
   - Permissions (CRUD operations)
   ```
4. **Select artifact type:** `mermaid_erd`
5. **Click "Build Context"** → Builds smart context
6. **Click "Generate"** → Creates ERD diagram
7. **View result** in Canvas (visual) or Code tab (Mermaid syntax)

**Behind the scenes:**
- Universal Context loads your project (User, Session, Role models)
- RAG finds similar entities in your codebase
- Model generates ERD with YOUR naming conventions
- Validator checks quality (relationships, attributes, syntax)
- You get a diagram that **matches your existing architecture!**

---

### **Workflow 2: Chat About Your Project**

1. **Go to Studio** → **Chat** tab
2. **Ask:** "How does authentication work in our project?"
3. **System:**
   - Loads Universal Context (knows all files)
   - RAG retrieves: `AuthService.cs`, `UserModel.py`, `LoginController.ts`
   - Ranks by importance (AuthService > LoginController)
   - Generates answer using YOUR code
4. **You get:** Detailed explanation with code snippets from YOUR project

---

### **Workflow 3: Analyze Project Patterns**

1. **Go to Intelligence** page
2. **Knowledge Graph section** → Click "Refresh"
   - Shows: Classes, Functions, Relationships from YOUR code
   - Example: `AuthService → uses → UserRepository → accesses → UserModel`
3. **Pattern Mining section** → Click "Refresh"
   - Shows: Singleton (AuthService), Factory (TokenFactory), etc.
4. **Universal Context section** → Shows stats
   - Files indexed: 1250
   - Key entities: 50
   - Patterns: 23

---

## 🔧 Configuration & Customization

### **Adjust Importance Scoring**

Edit: `backend/services/universal_context.py`

```python
def _calculate_file_importance(self, file_path: Path) -> float:
    # Custom scoring for your project structure
    if 'critical' in str(file_path):
        return 1.0
    if 'legacy' in str(file_path):
        return 0.2  # Deprioritize legacy code
    # ... rest of logic
```

---

### **Add Custom Model**

Edit: `model_routing.yaml`

```yaml
mermaid_erd:
  primary_model: "ollama:deepseek-coder:6.7b"
  fallback_models:
    - "ollama:qwen2.5-coder:7b"
    - "gemini:gemini-2.0-flash"
    - "ollama:my-custom-model:13b"  # ← Add your model
  enabled: true
```

---

### **Adjust Validation Thresholds**

Edit: `backend/services/validation_service.py`

```python
VALIDATION_THRESHOLD = 60  # Change to 70 for stricter validation
```

---

### **Cache Duration (Universal Context)**

Edit: `backend/services/universal_context.py`

```python
self._cache_ttl = timedelta(hours=12)  # Default: 6 hours
```

---

## 🐛 Troubleshooting

### **Issue: "Ollama not available"**

**Symptoms:**
- Generation always uses cloud models
- Logs show: "Ollama not responding"

**Fix:**
```powershell
# Check if Ollama is running
ollama list

# If not, start it
ollama serve

# Or restart the service
net stop ollama
net start ollama
```

---

### **Issue: "Universal Context not built"**

**Symptoms:**
- Intelligence page shows "Not yet built"
- Artifacts lack project context

**Fix:**
1. Click "Build Now" in Intelligence page
2. Or restart backend (auto-builds on startup)
3. Check logs for errors

---

### **Issue: "Low validation scores (< 60)"**

**Symptoms:**
- Artifacts keep getting regenerated
- Never converges to acceptable quality

**Fix:**
1. **Improve requirements** - Be more specific in meeting notes
2. **Use better model** - Try GPT-4 instead of codellama
3. **Lower threshold** temporarily:
   ```python
   VALIDATION_THRESHOLD = 50  # In validation_service.py
   ```
4. **Check context quality** - Is RAG retrieving relevant code?

---

### **Issue: "Out of VRAM errors"**

**Symptoms:**
- Ollama crashes during generation
- Logs show: "CUDA out of memory"

**Fix:**
1. **Use smaller model:**
   ```yaml
   primary_model: "ollama:codellama:7b"  # Instead of 13b
   ```
2. **Use 4-bit quantization:**
   ```powershell
   ollama pull deepseek-coder:6.7b-instruct-q4_K_M
   ```
3. **Close other GPU apps** (games, Chrome with hardware acceleration)

---

### **Issue: "RAG not finding my code"**

**Symptoms:**
- Generated artifacts don't reference your entities
- Context seems generic

**Fix:**
1. **Check if files are indexed:**
   ```bash
   GET /api/universal-context/status
   # Should show total_files > 0
   ```
2. **Verify project directory is correct:**
   - Should be parent of `architect_ai_cursor_poc`
   - Not `architect_ai_cursor_poc` itself
3. **Rebuild Universal Context:**
   ```bash
   POST /api/universal-context/rebuild
   ```
4. **Check exclusions** in `backend/utils/tool_detector.py`

---

## 📈 Performance Metrics (Expected)

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| **Startup (first time)** | 15-30 seconds | Indexes entire project |
| **Startup (cached)** | 5-10 seconds | Universal Context from cache |
| **Context Building** | 1-3 seconds | Universal + targeted RAG |
| **Ollama Generation** | 5-15 seconds | Depends on model size |
| **Cloud Generation** | 2-8 seconds | Network latency + API time |
| **Validation** | 0.5-2 seconds | 8 validators in parallel |
| **Total (E2E)** | 10-25 seconds | Requirements → artifact |

**For a 1000-file project:**
- Initial index: ~10 seconds
- Universal Context build: ~12 seconds
- Per-query retrieval: ~100ms

---

## 🎉 Summary - Why This Is Powerful

### **Before (Generic AI Tools):**
```
User: "Create user auth system"
AI: "Here's a generic ERD with User and Password tables"
     (Doesn't know YOUR project, YOUR conventions, YOUR architecture)
```

### **After (Architect.AI with Universal Context):**
```
User: "Create user auth system"

System: 
  ✅ Loads Universal Context (knows 1250 files)
  ✅ Finds YOUR existing entities (UserModel, AuthService, SessionManager)
  ✅ Identifies YOUR patterns (Singleton, Repository pattern)
  ✅ Ranks by importance (core logic > tests)
  ✅ Generates ERD that MATCHES your architecture
  
AI: "Here's an ERD that:
     - Uses YOUR UserModel fields (email, password_hash, role_id)
     - Follows YOUR naming (snake_case for DB, PascalCase for C#)
     - Connects to YOUR existing RoleModel
     - Includes YOUR SessionManager token structure"
```

**Result:** Artifacts that feel like YOU wrote them, not a generic AI!

---

## 🚀 Next Steps

1. **Test the complete flow** (Canvas → Requirements → Generate → View)
2. **Check Universal Context status** (Intelligence page)
3. **Try different artifact types** (ERD, Architecture, Sequence diagrams)
4. **Explore Knowledge Graph** (see your project structure)
5. **Chat about your project** (test RAG intelligence)
6. **Configure models** (add/remove from routing)
7. **Fine-tune on feedback** (improve quality over time)

---

**This is how it all works!** 🎯

Every piece is connected. Universal Context is the foundation that makes everything intelligent.

**Version:** 1.0.0  
**Date:** November 24, 2025  
**Status:** ✅ Production Ready

