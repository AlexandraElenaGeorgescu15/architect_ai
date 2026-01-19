# Architect.AI Demo Guide 🎬

## Pre-Demo Checklist

### 1. Verify Services Are Running
```bash
# Run the quick health check
python scripts/demo_health_check.py
```

### 2. Start the Application
```bash
# Windows
launch.bat

# Linux/Mac  
./launch.sh
```

### 3. Open in Browser
- Frontend: http://localhost:3000
- Backend API Docs: http://localhost:8000/api/docs

---

## Demo Flow (15-20 minutes)

### Part 1: Introduction (2 min)
**What to say:**
> "Architect.AI transforms your requirements into production-ready software artifacts. Unlike generic AI tools, it learns YOUR codebase and generates context-aware outputs."

**Show:**
- Landing page with the premium UI
- Mention: 50+ artifact types, multi-model support, 5-layer intelligence

---

### Part 2: Meeting Notes & Context (3 min)
**What to say:**
> "Start by selecting or creating a meeting notes folder. This is where you capture requirements from stakeholder meetings."

**Demo steps:**
1. Click on **Studio** tab
2. Select "E-Commerce Platform" folder (or create new)
3. Show the meeting notes content
4. Click "Build Context" to trigger RAG indexing
5. Point out the context sources: RAG chunks, Knowledge Graph, Patterns

**Key talking points:**
- Artifacts are now SCOPED to the selected folder
- Different projects = different contexts = different outputs

---

### Part 3: Generate an Artifact (4 min)
**What to say:**
> "Now let's generate some artifacts. Watch how the system uses the indexed context."

**Demo steps:**
1. Select artifact type using the **Category Tabs** (Mermaid → ERD Diagram)
2. Click "Generate"
3. Show the real-time progress (WebSocket streaming)
4. When complete, show the generated ERD
5. Click to view in Canvas editor (if time permits)

**Try these artifact types:**
- `mermaid_erd` - Database schema from requirements
- `mermaid_architecture` - System architecture diagram
- `mermaid_sequence` - API flow visualization
- `code_prototype` - Working code with tests
- `jira` - User stories and tasks

---

### Part 4: Custom Artifact Types (2 min)
**What to say:**
> "What if you need an artifact type we don't have? Users can create their own."

**Demo steps:**
1. Click the **"Custom"** button next to artifact selector
2. Create a new type:
   - ID: `security_review`
   - Name: "Security Review"
   - Category: "Security"
   - Template: Show the prompt template
3. Generate using the new custom type

---

### Part 5: Model Management (3 min)
**What to say:**
> "Not sure which model to use? Ask AI for recommendations."

**Demo steps:**
1. Go to **Intelligence** page → Model Mapping tab
2. Find an artifact type row
3. Click **"Ask AI"** button
4. Show the recommendation with confidence score
5. Click "Apply" to use the suggestion
6. Show the HuggingFace model search (if time)

---

### Part 6: Agentic Chat with Write Mode (4 min)
**What to say:**
> "The chat isn't just Q&A - it's an intelligent agent that can explore your codebase AND modify artifacts."

**Demo steps:**
1. Open the floating chat (bottom-right bubble)
2. Show **Agent Mode** toggle (enabled by default)
3. Ask: "What authentication methods are used in the e-commerce platform?"
4. Watch the agent search the codebase (tool status updates)
5. Enable **Write Mode** (show the confirmation dialog)
6. Ask: "Create an ERD diagram focusing on user authentication"
7. Show that the agent created/updated an artifact

**Key talking points:**
- Agent mode: AI autonomously searches when needed
- Write mode: Controlled artifact modification (user must enable)
- Safety: Write mode is OFF by default

---

### Part 7: Q&A Wrap-up (2 min)

**Key differentiators to emphasize:**
1. **Context-aware**: Uses YOUR codebase, not generic templates
2. **Multi-model**: Local (Ollama) or cloud (Gemini, GPT-4, Groq)
3. **Extensible**: Custom artifact types, custom categories
4. **Safe**: Write operations require explicit user consent
5. **Production-ready**: Validation, retry logic, quality scoring

---

## Quick Demo Commands

### Generate multiple artifacts quickly:
1. E-Commerce ERD → Architecture → API Sequence
2. Healthcare API Docs → Jira Tasks → Estimations
3. FinTech Dashboard → Code Prototype → Personas

### Impressive one-liners for chat:
- "Explain the data flow between the cart and checkout services"
- "What design patterns are used in this codebase?"
- "Generate a security review for the payment processing module"
- "Create a C4 context diagram for the entire system"

---

## Troubleshooting

### Backend not starting?
```bash
# Check if port 8000 is in use
netstat -an | findstr 8000

# Verify Python environment
python --version
pip list | findstr fastapi
```

### Frontend not loading?
```bash
# Check Node version
node --version

# Reinstall dependencies
cd frontend && npm install
```

### Ollama models not showing?
```bash
# Check if Ollama is running
ollama list

# Pull a model if needed
ollama pull llama3:8b-instruct-q4_K_M
```

### Chat not responding?
- Check if Groq API key is set: Settings → API Keys
- Verify Ollama is running for local models
- Check browser console for errors

---

## Post-Demo Follow-up

Share these resources:
- GitHub repo link
- API documentation: http://localhost:8000/api/docs
- This demo guide
- Contact for questions
