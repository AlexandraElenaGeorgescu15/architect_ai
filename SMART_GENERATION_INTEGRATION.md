# Smart Generation System Integration Guide

## Overview

The new smart generation system (`ai/smart_generation.py`) implements an intelligent local-first architecture with cloud fallback and fine-tuning data capture.

## Architecture

```
User Request
    ↓
SmartGenerationOrchestrator
    ↓
Try Priority Model 1 (Local) → Validate → Pass? → Return ✅
    ↓ Failed
Try Priority Model 2 (Local) → Validate → Pass? → Return ✅
    ↓ Failed
Try Priority Model 3 (Local) → Validate → Pass? → Return ✅
    ↓ Failed
Cloud Fallback (Gemini/GPT-4) → Validate → Save for Fine-tuning → Return
```

## Key Components

### 1. Smart Generation Orchestrator (`ai/smart_generation.py`)

**Responsibilities:**
- Manages the entire generation lifecycle
- Selects best local model for artifact type
- Validates output quality with strict thresholds
- Falls back to cloud only when local fails
- Captures cloud responses for fine-tuning

**Usage:**
```python
from ai.smart_generation import get_smart_generator

orchestrator = get_smart_generator(
    ollama_client=ollama_client,
    output_validator=output_validator,
    min_quality_threshold=80
)

result = await orchestrator.generate(
    artifact_type="mermaid_erd",
    prompt=prompt,
    system_message=system_message,
    cloud_fallback_fn=cloud_fallback_function,
    meeting_notes=meeting_notes,
    context={"meeting_notes": meeting_notes}
)

if result.success:
    print(f"Generated with {result.model_used}")
    print(f"Quality: {result.quality_score}/100")
    print(f"Cloud fallback: {result.used_cloud_fallback}")
```

### 2. Output Validator (`ai/output_validator.py`)

**Enhancements:**
- Added semantic validation (checks if content matches meeting notes)
- Artifact-specific validation rules
- Quality scoring (0-100)

**Key Methods:**
```python
from ai.output_validator import get_validator, ValidationResult
from ai.artifact_router import ArtifactType

validator = get_validator()
result, errors, score = validator.validate(
    ArtifactType.ERD,
    content,
    context={"meeting_notes": meeting_notes}
)
```

### 3. Mermaid Editor (`components/mermaid_editor.py`)

**Simplified:**
- Removed AI-generated diagram editor complexity
- Simple canvas-based approach:
  - Left: Syntax editor with validation
  - Right: Live preview with mermaid.js
- Syntax validation before rendering
- Clean, focused UX

**Usage:**
```python
from components.mermaid_editor import render_mermaid_editor

updated_code = render_mermaid_editor(
    initial_code=mermaid_diagram,
    key="unique_key"
)
```

## Integration with Universal Agent

### Current State

The `UniversalArchitectAgent._call_ai()` method currently has partial local-first logic:
1. Tries Ollama if available
2. Falls back to cloud on failure
3. Has some quality validation

### Needed Integration

Replace the current `_call_ai()` logic with the smart generation orchestrator for all artifact generation:

```python
async def _call_ai_with_smart_generation(
    self,
    prompt: str,
    system_prompt: str = None,
    artifact_type: str = None,
    **kwargs
) -> str:
    """Use smart generation orchestrator for all artifacts."""
    
    # Initialize orchestrator
    from ai.smart_generation import get_smart_generator
    from ai.output_validator import get_validator
    
    orchestrator = get_smart_generator(
        ollama_client=self.ollama_client,
        output_validator=get_validator(),
        min_quality_threshold=80
    )
    
    # Define cloud fallback function
    async def cloud_fallback(prompt, system_message, artifact_type, **kwargs):
        # Use existing cloud provider logic
        return await self._call_cloud_provider(prompt, system_message)
    
    # Generate with smart orchestrator
    result = await orchestrator.generate(
        artifact_type=artifact_type or "documentation",
        prompt=prompt,
        system_message=system_prompt,
        cloud_fallback_fn=cloud_fallback,
        meeting_notes=self.meeting_notes,
        context={"meeting_notes": self.meeting_notes}
    )
    
    if result.success:
        return result.content
    else:
        raise Exception(f"Generation failed: {result.validation_errors}")
```

## Artifact Type Mapping

The orchestrator uses these artifact types:

### Diagrams
- `mermaid_erd` - Entity Relationship Diagrams
- `mermaid_architecture` - System Architecture Diagrams
- `mermaid_sequence` - Sequence Diagrams
- `mermaid_class` - Class Diagrams
- `mermaid_state` - State Machine Diagrams
- `mermaid_flowchart` - Flowcharts

### Code & Prototypes
- `code_prototype` - General code prototypes
- `typescript_code` - TypeScript code
- `csharp_code` - C# code
- `html_diagram` - HTML diagrams
- `visual_prototype` - Visual HTML prototypes

### Documentation
- `jira_stories` - JIRA user stories
- `api_docs` - API documentation
- `workflows` - Workflow documentation
- `documentation` - General documentation

### PM Mode
- `pm_analysis` - PM analysis
- `pm_planning` - PM planning
- `pm_tasks` - PM task breakdown

## Fine-Tuning Data Capture

Cloud responses are automatically saved to `finetune_datasets/cloud_responses/`:

```json
{
  "artifact_type": "mermaid_erd",
  "prompt": "...",
  "system_message": "...",
  "cloud_response": "...",
  "quality_score": 95.0,
  "timestamp": "2025-11-09T...",
  "local_model_failed": "mistral:7b-instruct-q4_K_M",
  "meeting_notes": "..."
}
```

These can be used for:
1. Fine-tuning local models
2. Quality benchmarking
3. Model improvement tracking

## Quality Thresholds

Default: 80/100

Artifact-specific thresholds can be adjusted in `SmartGenerationOrchestrator.artifact_models`.

## Testing

Test the complete flow:

```python
# 1. Test local generation (should pass)
result = await orchestrator.generate(
    artifact_type="mermaid_erd",
    prompt="Create ERD for phone swap feature",
    system_message="You are an expert data modeler",
    meeting_notes="Feature: Phone swap request modal"
)

# 2. Test validation failure → cloud fallback
# (Use a deliberately poor prompt or disable good local models)

# 3. Test fine-tuning data capture
# Check finetune_datasets/cloud_responses/ for JSON files
```

## Migration Path

1. ✅ Create `ai/smart_generation.py`
2. ✅ Update `components/mermaid_editor.py` 
3. ✅ Enhance `ai/output_validator.py` with semantic validation
4. 🔄 Integrate into `UniversalArchitectAgent._call_ai()`
5. 🔄 Test all artifact types
6. 🔄 Monitor fine-tuning data collection
7. 🔄 Run fine-tuning jobs when data reaches threshold

## Benefits

1. **Cost Reduction**: Local models free, cloud only when needed
2. **Quality Assurance**: Strict validation before accepting output
3. **Continuous Improvement**: Fine-tuning from cloud responses
4. **User Experience**: Faster responses from local models
5. **Transparency**: Clear quality scores and fallback reasons
6. **Simplicity**: Clean Mermaid editor without AI complexity

## Next Steps

1. Wire up the smart generator in universal agent
2. Test with all artifact types
3. Monitor fine-tuning data accumulation
4. Set up automated fine-tuning jobs
5. Track quality improvements over time
