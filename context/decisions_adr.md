# Architect.AI - Architecture Decision Records

## ADR-001: Migration from Streamlit to FastAPI + React

**Date:** November 2025  
**Status:** Accepted  
**Deciders:** Development Team

### Context
The original Streamlit-based application (v2.x) became difficult to maintain and scale:
- Monolithic 6000+ LOC file mixing UI and business logic
- Limited customization of UI components
- No real-time updates capability
- Poor separation of concerns

### Decision
Migrate to FastAPI (backend) + React (frontend) architecture.

### Consequences
**Positive:**
- Clean separation of concerns
- Real-time updates via WebSocket
- Better testability
- Scalable architecture
- Professional UI with Tailwind CSS

**Negative:**
- Learning curve for React/TypeScript
- More complex deployment
- Legacy code maintenance during transition

---

## ADR-002: SQLite as Primary Database

**Date:** November 2025  
**Status:** Accepted

### Context
Need persistent storage for artifacts, versions, feedback, and user data.

### Decision
Use SQLite for simplicity and portability.

### Consequences
**Positive:**
- Zero configuration
- Single file database
- Easy backup and restore
- Sufficient for single-user/small team use

**Negative:**
- Not suitable for high concurrency
- No built-in replication

**Migration Path:** Can migrate to PostgreSQL if needed.

---

## ADR-003: ChromaDB for Vector Storage

**Date:** October 2025  
**Status:** Accepted

### Context
RAG system requires vector storage for semantic search.

### Decision
Use ChromaDB for vector storage.

### Consequences
**Positive:**
- Easy to set up (embedded mode)
- Good performance for medium-scale data
- Python-native API

**Negative:**
- Limited to local/embedded mode in current setup
- May need to migrate to hosted solution for scale

---

## ADR-004: Multi-Model Support

**Date:** October 2025  
**Status:** Accepted

### Context
Different artifact types may benefit from different AI models.

### Decision
Implement multi-model support with smart routing:
- Local: Ollama (DeepSeek, Llama, Mistral)
- Cloud: Gemini, GPT-4, Groq, Claude

### Consequences
**Positive:**
- Flexibility in model selection
- Cost optimization
- Fallback options

**Negative:**
- Complexity in model management
- Need to handle different API formats

---

## ADR-005: Local Fine-tuning with LoRA

**Date:** November 2025  
**Status:** Accepted

### Context
Want to improve model performance based on user feedback.

### Decision
Implement local fine-tuning using LoRA/QLoRA with PEFT library.

### Consequences
**Positive:**
- Personalized model improvement
- Runs on consumer hardware
- No cloud training costs

**Negative:**
- Requires VRAM management
- Training time overhead

---

## ADR-006: Zustand for Frontend State

**Date:** November 2025  
**Status:** Accepted

### Context
Need state management for React frontend.

### Decision
Use Zustand instead of Redux.

### Consequences
**Positive:**
- Minimal boilerplate
- TypeScript support
- Easy to learn

**Negative:**
- Less ecosystem than Redux
- Fewer dev tools

---

## ADR-007: Self-Contamination Prevention

**Date:** October 2025  
**Status:** Accepted

### Context
RAG system should not index Architect.AI's own code to avoid circular references.

### Decision
Implement tool detector that excludes Architect.AI directories from indexing.

### Consequences
**Positive:**
- Clean RAG results
- No self-referential artifacts

**Negative:**
- Maintenance of exclusion patterns

---

## Template for New ADRs

```markdown
## ADR-XXX: Title

**Date:** YYYY-MM  
**Status:** Proposed | Accepted | Deprecated | Superseded  
**Deciders:** Names

### Context
What is the issue that we're seeing that is motivating this decision?

### Decision
What is the change that we're proposing and/or doing?

### Consequences
What becomes easier or more difficult to do because of this change?

**Positive:**
- ...

**Negative:**
- ...
```

