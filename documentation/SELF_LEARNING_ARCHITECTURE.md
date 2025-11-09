# Self-Learning AI Architecture

## Overview
This system implements a complete **reinforcement learning feedback loop** that learns from every production interaction. The AI improves itself automatically - "you wouldn't even improve the app by coding, just by using it."

## Architecture Diagram

```mermaid
graph TB
    subgraph "User Interaction"
        A[User Request] --> B[Universal Agent]
    end
    
    subgraph "Smart Preprocessing"
        C[Knowledge Graph Builder] --> |Component Relationships, Dependencies| D[RAG Context]
        E[Pattern Mining Detector] --> |Design Patterns, Quality Metrics| D
        F[Validation Pipeline] --> |Noise Reduction| D
    end
    
    subgraph "AI Generation - Try Local First"
        B --> G{Artifact Type?}
        G --> |HTML/Diagram| H[Try Local Model]
        G --> |Code/Text| H
        H --> I[Generate Output]
    end
    
    subgraph "Programmatic Validation"
        I --> J[Syntax Checker]
        J --> |Mermaid| K[Diagram Validator]
        J --> |HTML| L[Tag Balancer]
        K --> M[Calculate Noise Score]
        L --> M
    end
    
    subgraph "Context-Aware Quality Check"
        M --> N{Noise Score < 0.3?}
        N --> |Yes| O[Context Validator]
        N --> |No| P[Cloud Fallback]
        O --> Q{Quality Score >= 70%?}
        Q --> |No| P
        Q --> |Yes| R[Accept Output]
        P --> R
    end
    
    subgraph "Adaptive Learning Loop - THE CORE"
        R --> S[Record Feedback Event]
        S --> T[Calculate RL Reward]
        T --> U{User Feedback?}
        U --> |Correction| V[Negative Reward]
        U --> |Acceptance| W[Positive Reward]
        U --> |Explicit Feedback| X[Strong Reward]
        V --> Y[Update Event Store]
        W --> Y
        X --> Y
    end
    
    subgraph "Training Batch Creation (AUTOMATIC)"
        Y --> Z{5000+ Examples Ready?}
        Z --> |Yes| AA[Create Training Batch]
        AA --> AB[Generate JSONL Dataset]
        AB --> AC[Ready for Fine-Tuning]
        Z --> |No| AD[Keep Collecting]
    end
    
    subgraph "Manual Fine-Tuning Trigger"
        AC --> AE[User Clicks 'Start Fine-Tuning']
        AE --> AF[Background Training Worker]
        AF --> AG[Train Model (LoRA/QLoRA)]
        AG --> AH[Deploy Improved Model]
    end
    
    AH --> |Next Request| B
    
    style S fill:#ff9999
    style T fill:#ff9999
    style AA fill:#99ff99
    style AG fill:#9999ff
```

## Component Details

### 1. Smart Preprocessing (Pre-AI)

**Knowledge Graph Builder** (`components/knowledge_graph.py` - 752 lines)
```python
# Extracts component relationships WITHOUT AI (programmatic parsing)
- AST parsing for Python (imports, classes, functions)
- Regex parsing for TypeScript, C#, Java, C++ (classes, methods)
- NetworkX graph construction (nodes = components, edges = relationships)
- Metrics calculation (coupling, clustering coefficient, complexity)
- Lazy-load + cache (10x performance boost)
```

**Pattern Mining Detector** (`components/pattern_mining.py` - 967 lines)
```python
# Detects code patterns via static analysis
- Design patterns (Singleton, Factory, Observer, Strategy, Decorator)
- Anti-patterns (God Class >500 LOC, Long Method >50 LOC, Duplicate Code)
- Code smells (Magic Numbers, Dead Code/TODOs, Complex Conditionals)
- Quality scoring (0-100 based on detected issues)
- Complexity calculation (cyclomatic complexity)
```

**Validation Pipeline** (`components/validation_pipeline.py`)
```python
# Programmatic noise reduction
- Regex-based cleaning (comments, debug, whitespace)
- Stop-word removal (60+ common words)
- Keyword extraction (min 3 chars)
- Noise score: 0 (clean) → 1 (noisy)
```

### 2. Quality-Based Fallback

```python
# agents/universal_agent.py
async def _call_ai(self, prompt, context, artifact_type):
    # Try local first
    output = await ollama_client.generate(local_model, prompt)
    
    # Programmatic validation
    noise_score = validation_pipeline.calculate_noise(output)
    if noise_score >= 0.3:
        return await cloud_fallback()
    
    # Context-aware quality check
    quality_score = output_validator.validate(output, context)
    if quality_score < 70.0:
        return await cloud_fallback()
    
    return output
```

### 3. Adaptive Learning Loop (THE CORE)

**Every generation is recorded:**
```python
# components/adaptive_learning.py
@dataclass
class FeedbackEvent:
    timestamp: str
    artifact_type: str
    model_used: str
    input_prompt: str
    generated_output: str
    validation_score: float
    feedback_type: FeedbackType  # SUCCESS, USER_CORRECTION, etc.
    reward: float  # -1.0 to 1.0 (RL reward)
    context_snapshot: Dict
```

**Reward Calculation:**
```python
class RewardCalculator:
    def calculate(self, validation_score, feedback_type):
        # Base reward from validation
        base = (validation_score - 50) / 50  # -1 to 1
        
        # Boost/penalty from user feedback
        if feedback_type == FeedbackType.EXPLICIT_POSITIVE:
            return min(1.0, base + 0.5)
        elif feedback_type == FeedbackType.USER_CORRECTION:
            return -0.7
        
        return base
```

**Automatic Training Batches:**
```python
class AdaptiveLearningLoop:
    async def record_feedback(self, event: FeedbackEvent):
        # Save event (AUTOMATIC)
        await self._append_to_store(event)
        
        # Build comprehensive training batch (AUTOMATIC)
        # 5000+ examples from:
        # - Feedback events (user corrections, successes)
        # - RAG chunks (600-1200 examples)
        # - Builtin examples (88 diverse tech stacks)
        # - Repository sweep (200-400 files)
        training_batch = dataset_builder.build_dataset()
        
        # Training batch ready, but requires MANUAL trigger
        # User must click "Start Fine-Tuning" button
```

### 4. Manual Fine-Tuning Trigger

**Implementation** (`components/local_finetuning.py` - 2380 lines)
```python
# User clicks "Start Fine-Tuning" button in Fine-Tuning tab
# This triggers background training (prevents unsafe automatic updates)

if st.button("🚀 Start Fine-Tuning"):
    # Load training batches (5000+ examples)
    training_data = dataset_builder.build_dataset(
        feedback_examples=feedback_store.list_feedback(),
        rag_examples=rag_chunks,  # 600-1200 chunks
        builtin_examples=BUILTIN_EXAMPLES,  # 88 examples
        repo_sweep_examples=sweep_repository()  # 200-400 files
    )
    
    # Configure LoRA/QLoRA 4-bit fine-tuning
    config = TrainingConfig(
        model_name="codellama:7b",
        epochs=3,
        learning_rate=2e-4,
        batch_size=4,
        lora_rank=16,
        lora_alpha=32,
        use_4bit=True
    )
    
    # Start training (background thread)
    local_finetuning_system.start_training(config, training_data)
    # Loads previous version (incremental: v1 → v2 → v3)
    # Saves checkpoints every epoch (survives app restarts)
    # Auto-registers improved model for next generation
```

## Data Flow

### Example: User Generates ERD

1. **Request:** "Create ERD for user authentication"

2. **Preprocessing:**
   - Knowledge Graph Builder extracts User entity relationships
   - Pattern Mining Detector finds authentication patterns (Observer, Singleton)
   - Validation Pipeline reduces noise (removes comments, debug statements)
   - RAG retrieves authentication-related code chunks

3. **Generation:**
   - Try local model (llama3.2)
   - Generate Mermaid ERD

4. **Validation:**
   - Syntax check: Valid Mermaid?
   - Noise score: 0.15 (clean)
   - Context check: Has User, Auth, Session entities?
   - Quality score: 85% ✓

5. **Feedback Recording:**
   ```json
   {
     "feedback_type": "SUCCESS",
     "validation_score": 85.0,
     "reward": 0.7,
     "model_used": "llama3.2"
   }
   ```

6. **Learning:**
   - Event added to store (AUTOMATIC)
   - 5000+ examples ready (feedback + RAG + builtin + repo sweep) (AUTOMATIC)
   - User clicks "Start Fine-Tuning" button (MANUAL)
   - Training worker trains improved model (AUTOMATIC ONCE STARTED)
   - Incremental training: loads previous version (v1 → v2 → v3)
   - Saves checkpoints every epoch (survives app restarts)
   - Next ERD uses improved model! ✅

## Key Insights

### Why This Works

1. **Programmatic First:** Knowledge Graph (AST parsing) + Pattern Mining (static analysis) provide structured, accurate data before AI
2. **Quality Gating:** Only outputs with 60%+ validation score accepted (auto-retry up to 2 attempts)
3. **RL Rewards:** Every interaction contributes to training signal (-1 to +1)
4. **Automatic Batching:** 5000+ examples auto-generated (no manual dataset creation)
5. **Manual Training Trigger:** Prevents unsafe automatic model updates (safety gate)
6. **Incremental Training:** Models improve continuously (v1 → v2 → v3)

### The Vision (With Important Clarification)

> "From then on you wouldn't even improve the app by coding, just by using it"

This is achieved through:
- **Passive Learning:** Every generation = training data (AUTOMATIC)
- **Reward Signals:** Validation scores + user feedback = RL rewards (AUTOMATIC)
- **Automatic Batching:** 5000+ examples auto-generated (AUTOMATIC)
- **Manual Training Trigger:** User clicks "Start Fine-Tuning" button (SAFETY GATE)
- **Automatic Model Improvement:** Once triggered, training runs in background (AUTOMATIC)
- **Incremental Updates:** Loads previous version, trains, deploys improved model (v1 → v2 → v3)

**Important:** The system collects feedback automatically, but requires manual training trigger to prevent unsafe production updates. This is intentional for safety and control.

## Integration Checklist

### Phase 1: Core Intelligence (✅ COMPLETE)
- [x] Integrate Knowledge Graph Builder (`components/knowledge_graph.py`)
- [x] Integrate Pattern Mining Detector (`components/pattern_mining.py`)
- [x] Hook up to Universal Agent (lazy-load + cache for 10x performance)
- [x] Inject into 5-layer context system

### Phase 2: Adaptive Learning (✅ COMPLETE)
- [x] Hook up `adaptive_loop.record_feedback()` in `universal_agent._call_ai()`
- [x] Pass validation scores to feedback recording
- [x] Track user corrections (edits to generated output)
- [x] Calculate RL rewards (-1 to +1)

### Phase 3: Fine-Tuning System (✅ COMPLETE)
- [x] Implement training batch builder (5000+ examples)
- [x] Create Fine-Tuning tab UI with manual trigger
- [x] Implement LoRA/QLoRA 4-bit fine-tuning
- [x] Add incremental training (v1 → v2 → v3)
- [x] Add checkpointing (survives app restarts)

### Phase 4: Validation & Quality (✅ COMPLETE)
- [x] Integrate 8 type-specific validators
- [x] Add auto-retry logic (up to 2 attempts, exponential backoff)
- [x] Add Mermaid syntax corrector (AI-powered, 3-pass iterative)

### Phase 5: Monitoring (⏳ PARTIAL)
- [x] Feedback event tracking
- [x] Validation reports (saved to `outputs/validation/`)
- [ ] Dashboard showing reward trends
- [ ] Training batch statistics UI
- [ ] Model performance over time graphs

## File Structure

```
components/
├── knowledge_graph.py              # AST + regex parsing → NetworkX graph (752 lines)
├── pattern_mining.py               # Design patterns + anti-patterns + code smells (967 lines)
├── validation_pipeline.py          # Noise reduction + keyword extraction (450 lines)
├── adaptive_learning.py            # RL feedback loop + training batches (408 lines)
├── local_finetuning.py             # LoRA/QLoRA fine-tuning (2380 lines)
├── automated_dataset_builder.py    # 5000+ example generation
└── feedback_collector.py           # Feedback event recording

validation/
└── output_validator.py             # 8 type-specific validators (750 lines)

finetune_datasets/
├── feedback/
│   ├── feedback_events_*.json      # All recorded feedback events
│   └── training_batch_*.jsonl      # Auto-generated training batches (5000+ examples)
└── builtin/
    └── diverse_examples.jsonl      # 88 builtin examples (diverse tech stacks)

finetuned_models/
├── codellama_7b/
│   ├── v1_20250101_120000/         # First fine-tuned version
│   ├── v2_20250102_140000/         # Incremental (loaded v1, trained, saved v2)
│   └── v3_20250103_160000/         # Incremental (loaded v2, trained, saved v3)
└── mistral_7b/
    └── v1_20250101_130000/

outputs/
└── validation/
    ├── erd_*.json                  # Validation reports for ERD
    ├── architecture_*.json         # Validation reports for Architecture
    └── code_*.json                 # Validation reports for Code
```

## Next Steps

1. **Monitoring Dashboard:** Add UI to visualize reward trends and model performance
2. **Automatic Training Trigger:** Add option for fully automatic training (with safety checks)
3. **Prompt Learning for Cloud Models:** Use feedback to optimize prompts for GPT-4/Gemini
4. **Quality-Based Routing:** Route to best model per artifact type based on historical performance
5. **Multi-Model Ensembles:** Combine multiple models for better quality

---

**Status:** Core systems ✅ COMPLETE, monitoring ⏳ PARTIAL  
**Priority:** Add monitoring dashboard (HIGH)  
**Note:** Manual training trigger is intentional for safety (prevents unsafe production updates)
