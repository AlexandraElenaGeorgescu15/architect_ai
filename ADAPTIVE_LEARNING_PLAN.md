# Architect.AI Adaptive Learning System - Implementation Plan

## Overview
Integrate immediate UX improvements with advanced learning capabilities to create a truly differentiated AI architect tool that learns from your repository and improves over time.

## Codebase Analysis Integration

### Current State Assessment (v2.5.2)
**Strengths (8/10):**
- ✅ Excellent architecture and design patterns
- ✅ Strong business value proposition  
- ✅ Good code organization and separation of concerns
- ✅ Innovative multi-agent approach
- ✅ Repository-aware generation
- ✅ RAG system with ChromaDB + BM25 hybrid search
- ✅ Multi-agent critique system for prototypes
- ✅ Version control and caching systems

**Critical Issues to Address:**
- ⚠️ **Monolithic UI**: `app_v2.py` is 4,176 lines - needs refactoring
- ⚠️ **Limited Testing**: No unit tests, only manual testing guide
- ⚠️ **Security Concerns**: API keys in session state, no authentication
- ⚠️ **Scalability Issues**: Single-user, local storage, no cloud readiness
- ⚠️ **Production Gaps**: No CI/CD, no API layer, no persistence

### Integration with Learning System

**Sprint 0: Technical Debt Resolution (Week 0-1)**
- Refactor monolithic UI into components
- Add comprehensive error handling and logging
- Implement proper API key management
- Add unit test framework
- Security hardening (authentication, input validation)

**Enhanced Sprint 1: Foundation + UX + Technical Debt**
- All original Sprint 1 features PLUS:
- UI refactoring into modular components
- Comprehensive error handling with actionable messages
- Security improvements (encrypted API keys, input sanitization)
- Basic unit tests for core functionality

## Integrated Implementation Roadmap

### Sprint 0: Technical Debt Resolution (Week 0-1)

#### A. UI Refactoring
**Files:** `app/app_v2.py`, `components/`
- Break down 4,176-line monolithic UI into modular components
- Create separate components for each major feature
- Implement proper component lifecycle management
- Add component-level error boundaries

#### B. Security Hardening
**Files:** `app/app_v2.py`, `utils/security.py`
- Encrypt API keys in session state
- Add input validation and sanitization
- Implement basic authentication system
- Add CSRF protection for forms

#### C. Testing Framework
**Files:** `tests/`, `pytest.ini`
- Add unit test framework (pytest)
- Create test fixtures for common scenarios
- Add integration tests for RAG system
- Implement test coverage reporting

### Sprint 1: Foundation + Immediate UX Wins (Week 1-2)

#### A. Better Error Messages & Progress Tracking
**Files:** `app/app_v2.py`, `agents/universal_agent.py`, `monitoring/logging_config.py`
- Replace generic error messages with specific, actionable guidance
- Add step-by-step progress bar for all generation tasks (10+ steps visible)
- Create `components/progress_tracker.py` with granular status updates
- Add ETA estimation based on historical generation times

#### B. Feedback Capture System (Learning Foundation)
**Files:** `db/models.py`, `components/feedback_collector.py`, `app/app_v2.py`
- Add database models: `GeneratedArtifact`, `UserFeedback`, `ArtifactEdit`
- Create UI for thumbs up/down on every generated artifact
- Track edit diffs when users modify generated code/docs
- Store acceptance/rejection/modification rates per artifact type
- Add "Why did you generate this?" explanation button

#### C. RAG Enhancement
**Files:** `rag/retrieve.py`, `rag/context_optimizer.py`, `agents/universal_agent.py`
- Increase RAG chunks from 18 to 50-100 with smart truncation
- Implement tiered context assembly (critical, important, supplementary)
- Add semantic code search to find most similar existing files
- Expand RAG queries to include repository-specific terms learned from analysis

### Sprint 2: Pattern Learning + Template Library (Week 3-4)

#### D. Repository Pattern Mining
**Files:** `analysis/pattern_miner.py`, `db/models.py`
- Create `RepositoryPattern` model (pattern_type, code_template, frequency, quality_score)
- Extract naming conventions from codebase (class names, function patterns, file structure)
- Mine code templates (service patterns, component structure, API controller templates)
- Detect architectural patterns (singleton, factory, repository pattern usage)
- Store learned patterns in database for reuse

#### E. Template Library System
**Files:** `components/template_library.py`, `agents/template_manager.py`
- Build UI for browsing learned templates
- Allow users to mark templates as "preferred" or "avoid"
- Auto-generate templates from most-used code patterns
- Pre-populate with common patterns (Angular component, .NET controller, etc.)
- Use templates as few-shot examples in generation prompts

#### F. Multi-Repository Support
**Files:** `rag/ingest.py`, `tenants/tenant_manager.py`, `app/app_v2.py`
- Add repository selector dropdown in UI
- Create separate ChromaDB collections per repository
- Track RAG index per repository with separate manifests
- Allow switching between repositories without re-indexing

### Sprint 3: Active Learning + Advanced Prompting (Week 5-6)

#### G. Self-Critique Loops for All Artifacts
**Files:** `agents/universal_agent.py`, `agents/quality_metrics.py`
- Extend multi-agent critique (Analyzer → Generator → Critic) to ALL artifacts
- Add revision loop: generate → critique → improve → validate
- Track quality improvement across iterations
- Store successful revision patterns

#### H. Chain-of-Thought & Specialized Prompts
**Files:** `agents/prompt_library.py`, `agents/universal_agent.py`
- Create specialized system prompts per artifact type (9 types)
- Implement chain-of-thought for complex generations (code, architecture)
- Add few-shot examples using learned repository patterns
- Build prompt evolution tracking (version, quality score, usage count)

#### I. Incremental RAG Updates ✅ COMPLETED
**Files:** `rag/file_watcher.py`, `rag/incremental_indexer.py`, `rag/auto_ingestion.py`
- ✅ Watch repository files for changes using `watchdog` library
- ✅ Update only changed chunks instead of full re-index
- ✅ Add background worker for continuous indexing
- ✅ Show "RAG updating..." indicator when changes detected
- ✅ Real-time UI integration with status monitoring
- ✅ Error recovery and graceful degradation

### Sprint 4: Knowledge Graph + Model Intelligence (Week 7-8)

#### J. Repository Knowledge Graph
**Files:** `analysis/knowledge_graph.py`, `db/models.py`
- Build graph database of component relationships (Neo4j or NetworkX)
- Map file dependencies, import patterns, co-change frequency
- Extract team conventions from commit messages
- Use graph for context-aware generation (understand "what fits where")

#### K. Advanced Model Routing
**Files:** `ai/model_router.py`, `ai/adaptive_selector.py`
- Track quality scores per model per artifact type
- Implement adaptive model selection based on historical performance
- Add ensemble generation: GPT-4 + Claude + Gemini, pick best via voting
- Enable parallel artifact generation with async execution

#### L. Parallel Artifact Generation
**Files:** `agents/parallel_orchestrator.py`, `app/app_v2.py`
- Generate multiple artifacts simultaneously (ERD + Architecture + API docs)
- Use asyncio for concurrent AI calls
- Show parallel progress in UI (multiple progress bars)
- Reduce total generation time by 60-70%

### Sprint 5: Fine-Tuning + Advanced Learning (Week 9-10)

#### M. Training Data Collection
**Files:** `learning/data_collector.py`, `learning/dataset_builder.py`
- Collect 500+ examples of (generated artifact → user's final version)
- Build training dataset in JSONL format for fine-tuning
- Track which patterns get accepted vs. rejected
- Create preference dataset for RLHF-lite

#### N. Local Model Fine-Tuning (Optional - Advanced)
**Files:** `ai/local_model.py`, `learning/fine_tune_pipeline.py`
- Set up CodeLlama 7B/13B fine-tuning pipeline
- Train on repository-specific patterns
- Deploy fine-tuned model locally (or via Hugging Face)
- Hybrid routing: local for style, cloud for reasoning

#### O. Self-Improving Prompt System
**Files:** `agents/prompt_evolution.py`, `learning/prompt_optimizer.py`
- A/B test prompt variations and track quality scores
- Use genetic algorithms to evolve better prompts
- Store winning prompts in database with version history
- Auto-select best-performing prompt per context

## Database Schema Changes

**New Models:**
```python
# db/models.py additions
class GeneratedArtifact(Base):
    id, artifact_type, content_hash, prompt_version, 
    rag_context_ids, model_used, quality_score, 
    user_feedback_score, was_accepted, edit_diff

class UserFeedback(Base):
    id, artifact_id, rating, comments, 
    accepted/rejected/modified, timestamp

class RepositoryPattern(Base):
    id, pattern_type, code_template, frequency, 
    quality_score, learned_from_files, last_updated

class PromptVersion(Base):
    id, artifact_type, prompt_text, system_prompt,
    avg_quality_score, usage_count, version_number

class RepositoryKnowledgeNode(Base):
    id, node_type, file_path, relationships, metadata
```

## Key Technical Decisions

**RAG Enhancement:**
- Increase k_final from 18 to 100 chunks
- Implement tiered assembly: top 20 critical (full), 30 important (partial), 50 supplementary (metadata only)
- Use `sentence-transformers/all-mpnet-base-v2` for better semantic search

**Model Strategy:**
- Keep Gemini Flash for simple tasks (free, fast)
- Use Groq Llama for medium tasks (free, very fast)
- Upgrade to GPT-4 or Claude Opus for code/architecture (quality over cost)
- Enable ensemble voting for critical artifacts

**Learning Approach:**
- Start with pattern mining (no ML required)
- Progress to preference learning (track what works)
- Consider fine-tuning only if 1000+ quality examples collected

## Success Metrics

**Quality Improvements:**
- Artifact acceptance rate: >70% → >90%
- User edit distance: <50% of generated content
- Quality scores: 75/100 → 90/100
- Time to usable artifact: 5 iterations → 1-2 iterations

**Learning Metrics:**
- Patterns learned per repository: 50-200
- Prompt improvement over time: +10% quality per month
- User feedback incorporation rate: 100%
- Model selection accuracy: >85% optimal model chosen

## Risks & Mitigations

**Risk:** Fine-tuning requires significant data
**Mitigation:** Start with pattern mining and few-shot learning, defer fine-tuning to Phase 5

**Risk:** Increased RAG context may hit token limits
**Mitigation:** Smart truncation with tiered importance, context compression

**Risk:** Parallel generation increases costs
**Mitigation:** Use free models (Gemini, Groq) where possible, make parallel optional

**Risk:** Learning system complexity
**Mitigation:** Incremental rollout, each sprint standalone value, backward compatible

## Next Steps After Approval

1. **Immediate:** Create database migrations for new models
2. **Week 0:** Technical debt resolution (UI refactoring, security, testing)
3. **Week 1:** Implement progress tracker + error messages (Sprint 1A)
4. **Week 1:** Add feedback capture UI (Sprint 1B)
5. **Week 2:** Enhance RAG context retrieval (Sprint 1C)
6. **Week 3:** Begin pattern mining implementation (Sprint 2D)
7. Continue through sprints with 2-week iterations

Each sprint delivers standalone value while building toward the complete adaptive learning system.

### To-dos

- [ ] **Sprint 0:** Refactor monolithic UI into components
- [ ] **Sprint 0:** Add security hardening (encrypted API keys, authentication)
- [ ] **Sprint 0:** Implement unit test framework
- [ ] **Sprint 1:** Implement better error messages and generation progress bar with ETA
- [ ] **Sprint 1:** Create feedback capture system (DB models, UI, edit tracking)
- [ ] **Sprint 1:** Enhance RAG: 100 chunks, tiered assembly, semantic code search
- [ ] **Sprint 2:** Add multi-repository support with separate collections
- [ ] **Sprint 2:** Build repository pattern mining system (conventions, templates, architecture)
- [ ] **Sprint 2:** Create template library with learned patterns and user preferences
- [ ] **Sprint 3:** Extend multi-agent self-critique loops to all artifact types
- [ ] **Sprint 3:** Implement chain-of-thought and specialized prompts per artifact type
- [x] **Sprint 3:** Implement incremental RAG updates with file watching ✅ COMPLETED
- [ ] **Sprint 4:** Build repository knowledge graph for context-aware generation
- [ ] **Sprint 4:** Implement adaptive model selection and ensemble generation
- [ ] **Sprint 4:** Enable parallel artifact generation with async execution
- [ ] **Sprint 5:** Collect training data from user edits and feedback for fine-tuning
- [ ] **Sprint 5:** Build self-improving prompt system with A/B testing and evolution
- [ ] **Sprint 5:** Optional: Fine-tune local model (CodeLlama) on repository patterns
