# 🎯 Model Routing Architecture Design

## Executive Summary

This document outlines the architecture for a **hybrid local/cloud AI model system** that routes artifact generation requests to specialized models, with intelligent fallback to cloud providers.

**Key Goals:**
1. Use local models (via Ollama) for speed, privacy, and cost savings
2. Load models on-demand, then keep them persistent
3. Fall back to cloud providers (Gemini/GPT-4) when local models fail
4. Provide clear UI feedback on which model is handling each request

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Request                             │
│              (Generate ERD, Code, JIRA, etc.)                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    Model Router                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Task Type Mapping:                                      │   │
│  │  • Mermaid Diagrams → MermaidMistral 7B                 │   │
│  │  • HTML/Code/Docs → CodeLlama 13B                       │   │
│  │  • JIRA Tasks → Llama 3 8B                              │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
┌────────▼───────┐              ┌───────▼────────┐
│ Local Models   │              │ Cloud Fallback │
│ (via Ollama)   │              │ (Gemini/GPT-4) │
│                │   ❌ Fail    │                │
│ [Loading...]   │──────────────>│   [Ready]      │
│ [Ready]        │              │                │
│ [In Use]       │              └────────────────┘
└────────────────┘
```

---

## 📦 Components

### 1. OllamaClient (`ai/ollama_client.py`)

**Purpose:** Interface to Ollama API (local model server)

**Responsibilities:**
- Connect to Ollama server (`http://localhost:11434`)
- Load models on-demand
- Track model status (not loaded / loading / ready / in use)
- Handle model inference requests
- Detect failures and trigger fallback

**API:**
```python
class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.loaded_models: Dict[str, ModelStatus] = {}
    
    async def load_model(self, model_name: str) -> bool:
        """Load model into memory (30-60 seconds first time)"""
        
    async def generate(self, model_name: str, prompt: str, **kwargs) -> str:
        """Generate text using loaded model"""
        
    def get_model_status(self, model_name: str) -> ModelStatus:
        """Get current status of model"""
        
    def list_available_models(self) -> List[str]:
        """List all models available in Ollama"""
```

**Model Status Enum:**
```python
class ModelStatus(Enum):
    NOT_LOADED = "not_loaded"    # Model not in memory
    LOADING = "loading"           # Model being loaded
    READY = "ready"               # Model loaded and ready
    IN_USE = "in_use"             # Model currently generating
    ERROR = "error"               # Model failed to load
```

---

### 2. ModelRouter (`ai/model_router.py` - **ENHANCED VERSION**)

**Purpose:** Route requests to appropriate models with fallback logic

**Responsibilities:**
- Map task types to models
- Attempt local model first
- Fall back to cloud on failure
- Track usage statistics
- Respect "Force Local Only" setting

**Enhanced API:**
```python
class ModelRouter:
    def __init__(self, ollama_client: OllamaClient, cloud_client: UniversalArchitectAgent):
        self.ollama = ollama_client
        self.cloud = cloud_client
        self.task_model_map = {
            'mermaid': 'mermaid-mistral',
            'html': 'codellama:13b-instruct-q4_K_M',
            'code': 'codellama:13b-instruct-q4_K_M',
            'documentation': 'codellama:13b-instruct-q4_K_M',
            'jira': 'llama3:8b-instruct-q4_K_M'
        }
        self.usage_stats = {}
        self.force_local_only = False
    
    async def generate(self, task_type: str, prompt: str, **kwargs) -> ModelResponse:
        """
        Generate using local model with fallback to cloud.
        
        Returns:
            ModelResponse with content, model_used, is_fallback, etc.
        """
        
    def get_model_for_task(self, task_type: str) -> str:
        """Get local model name for task type"""
        
    def set_force_local_only(self, enabled: bool):
        """Enable/disable cloud fallback"""
        
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
```

**ModelResponse:**
```python
@dataclass
class ModelResponse:
    content: str                 # Generated text
    model_used: str              # Model name that generated it
    is_fallback: bool            # True if cloud fallback was used
    generation_time: float       # Time taken in seconds
    tokens_used: int             # Approximate token count
    error_message: str = ""      # Error if any
```

---

### 3. Ollama Model Definitions

**Based on user requirements:**

| Task Type | Model Name | Ollama Pull Command | Size | Quantization |
|-----------|------------|---------------------|------|--------------|
| Mermaid Diagrams | `mermaid-mistral` | Custom (GGUF) | 4.5GB | Q4_K_M |
| HTML Generation | `codellama:13b-instruct-q4_K_M` | `ollama pull codellama:13b-instruct-q4_K_M` | ~7GB | Q4_K_M |
| Code Generation | `codellama:13b-instruct-q4_K_M` | (same) | ~7GB | Q4_K_M |
| Documentation | `codellama:13b-instruct-q4_K_M` | (same) | ~7GB | Q4_K_M |
| JIRA Tasks | `llama3:8b-instruct-q4_K_M` | `ollama pull llama3:8b-instruct-q4_K_M` | ~4.7GB | Q4_K_M |

**Total VRAM Usage (when all loaded):** ~16-20GB
**Recommended Hardware:** NVIDIA RTX 4090 (24GB VRAM) or similar

---

### 4. UI Integration (`app/app_v2.py`)

**Sidebar - Model Status Panel:**
```python
def render_model_status_panel():
    """Show status of all local models"""
    st.markdown("### 🤖 Model Status")
    
    for task_type, model_name in router.task_model_map.items():
        status = ollama_client.get_model_status(model_name)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{task_type.title()}**")
            st.caption(model_name)
        with col2:
            if status == ModelStatus.READY:
                st.success("Ready")
            elif status == ModelStatus.LOADING:
                st.warning("Loading...")
            elif status == ModelStatus.IN_USE:
                st.info("In Use")
            elif status == ModelStatus.ERROR:
                st.error("Error")
            else:
                st.caption("Not Loaded")
```

**Sidebar - Force Local Toggle:**
```python
force_local = st.checkbox(
    "🔒 Force Local Only",
    value=False,
    help="Never fall back to cloud providers. Fail if local model unavailable."
)
router.set_force_local_only(force_local)
```

**Generation Feedback:**
```python
response = await router.generate(task_type="mermaid", prompt=prompt)

if response.is_fallback:
    st.warning(f"⚠️ Local model unavailable. Used {response.model_used} (cloud) instead.")
else:
    st.info(f"✅ Generated using {response.model_used} (local) in {response.generation_time:.1f}s")
```

---

## 🔄 Workflow: On-Demand Loading

### First Request (Model Not Loaded)

```
1. User clicks "Generate ERD"
   │
2. Router determines task needs "mermaid-mistral"
   │
3. Router checks: is "mermaid-mistral" loaded?
   │
   ├─> NO (not loaded)
   │
4. Show loading UI:
   st.info("🔄 Loading MermaidMistral model (first time: ~30-60s)...")
   │
5. OllamaClient.load_model("mermaid-mistral")
   │
   ├─> SUCCESS: Model loaded
   │   │
   │   6. Generate diagram
   │   7. Cache model in memory
   │   8. Show result
   │
   ├─> FAILURE: Model failed to load
       │
       7. Check "Force Local Only" setting
       │
       ├─> Enabled: st.error("❌ Local model failed. Force Local enabled.")
       │
       ├─> Disabled: st.warning("⚠️ Local model failed. Falling back to Gemini...")
           │
           8. router.cloud.generate(prompt)
           9. Show result with fallback warning
```

### Subsequent Requests (Model Already Loaded)

```
1. User clicks "Generate ERD" (again)
   │
2. Router determines task needs "mermaid-mistral"
   │
3. Router checks: is "mermaid-mistral" loaded?
   │
   ├─> YES (already loaded)
   │
4. Generate immediately (5-10 seconds)
5. Show result
```

---

## 🛡️ Fallback Logic

### Decision Tree

```
┌─────────────────────────────┐
│ Local Model Available?      │
└──────┬──────────────────────┘
       │
   ┌───▼───┐
   │  YES  │──────> Use Local Model
   └───────┘
       │
       ❌ FAIL
       │
┌──────▼──────────────────────┐
│ Force Local Only Enabled?   │
└──────┬──────────────────────┘
       │
   ┌───▼───┐
   │  YES  │──────> st.error("Local model failed. Cannot fallback.")
   └───────┘
       │
   ┌───▼───┐
   │   NO  │──────> Fall back to Cloud (Gemini/GPT-4)
   └───────┘
```

### Fallback Reasons

1. **Model Not Installed:** User hasn't pulled model from Ollama
2. **Loading Failed:** Insufficient VRAM, corrupted model
3. **Generation Timeout:** Model takes too long (>120s)
4. **Generation Error:** Model produces invalid output
5. **Ollama Server Down:** Ollama not running

---

## 📊 Usage Statistics

**Track for each model:**
- Total requests
- Successful generations
- Fallbacks to cloud
- Average generation time
- Total tokens generated

**Dashboard (optional future tab):**
```
┌────────────────────────────────────────┐
│ Model Usage Statistics                 │
├────────────────────────────────────────┤
│ MermaidMistral:                        │
│ • Total: 47 requests                   │
│ • Success: 45 (95.7%)                  │
│ • Fallbacks: 2 (4.3%)                  │
│ • Avg Time: 8.3s                       │
│                                        │
│ CodeLlama 13B:                         │
│ • Total: 23 requests                   │
│ • Success: 22 (95.7%)                  │
│ • Fallbacks: 1 (4.3%)                  │
│ • Avg Time: 12.1s                      │
└────────────────────────────────────────┘
```

---

## 🚀 Implementation Plan

### Phase 1: Core Infrastructure
1. ✅ Create `OllamaClient` class
2. ✅ Enhance `ModelRouter` with Ollama support
3. ✅ Add model status tracking
4. ✅ Implement on-demand loading logic

### Phase 2: Model Integration
1. ✅ Integrate MermaidMistral for diagrams
2. ✅ Integrate CodeLlama 13B for code/HTML/docs
3. ✅ Integrate Llama 3 8B for JIRA tasks
4. ✅ Test each model independently

### Phase 3: UI & Feedback
1. ✅ Add model status panel to sidebar
2. ✅ Add "Force Local Only" toggle
3. ✅ Add generation feedback messages
4. ✅ Add progress indicators for loading

### Phase 4: Fallback & Error Handling
1. ✅ Implement cloud fallback logic
2. ✅ Add timeout handling
3. ✅ Add error recovery
4. ✅ Add usage statistics tracking

---

## 🧪 Testing Strategy

### Unit Tests
- `test_ollama_client.py` - Test Ollama API connection
- `test_model_router.py` - Test routing logic
- `test_fallback_logic.py` - Test cloud fallback

### Integration Tests
- Test each model with sample prompts
- Test on-demand loading
- Test fallback scenarios
- Test "Force Local Only" mode

### Performance Tests
- Measure loading times
- Measure generation times
- Measure VRAM usage
- Compare local vs cloud latency

---

## 📝 Configuration

### `config/ollama_config.yaml`
```yaml
ollama:
  base_url: "http://localhost:11434"
  timeout: 120  # seconds
  max_retries: 2
  
models:
  mermaid-mistral:
    name: "mermaid-mistral"
    task_types: ["mermaid", "diagram", "erd", "architecture"]
    quantization: "Q4_K_M"
    size_gb: 4.5
    
  codellama-13b:
    name: "codellama:13b-instruct-q4_K_M"
    task_types: ["code", "html", "documentation"]
    quantization: "Q4_K_M"
    size_gb: 7.0
    
  llama3-8b:
    name: "llama3:8b-instruct-q4_K_M"
    task_types: ["jira", "tasks", "planning"]
    quantization: "Q4_K_M"
    size_gb: 4.7

fallback:
  enabled: true
  cloud_provider: "gemini"  # or "openai"
  force_local_default: false
```

---

## 🎯 Success Criteria

- ✅ All local models load successfully on first request
- ✅ Subsequent requests use cached models (fast)
- ✅ Cloud fallback works when local fails
- ✅ UI shows clear feedback on which model is used
- ✅ "Force Local Only" prevents cloud fallback
- ✅ Generation time: Local < 15s, Cloud < 30s
- ✅ VRAM usage stays under 20GB (with 3 models loaded)

---

## 🚧 Future Enhancements

1. **Model Warm-Up:** Preload all models at startup (optional)
2. **Model Unloading:** Free VRAM by unloading unused models
3. **Model Prioritization:** Load most-used models first
4. **Multi-Model Ensemble:** Generate with multiple models, pick best
5. **Custom Model Registration:** Allow users to add their own Ollama models
6. **GPU Monitoring:** Show real-time VRAM usage chart

---

**Status:** 🎯 READY FOR IMPLEMENTATION  
**Date:** November 6, 2025  
**Next Step:** Implement `OllamaClient`

