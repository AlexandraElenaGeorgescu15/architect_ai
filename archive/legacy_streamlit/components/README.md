# Legacy Streamlit Components

This directory contains Python components from the original Streamlit-based application (v2.x).

## Contents

These components were designed for Streamlit and have been replaced by:
- **Backend services:** `backend/services/` (FastAPI)
- **Frontend components:** `frontend/src/components/` (React)

### Archived Components

These are pure Streamlit UI components that have been replaced:

| Component | Replaced By |
|-----------|-------------|
| `metrics_dashboard.py` | `frontend/src/pages/Intelligence.tsx` |
| `finetuning_ui.py` | `frontend/src/pages/Intelligence.tsx` |
| `ollama_ui.py` | `frontend/src/pages/Intelligence.tsx` |
| `diagram_viewer.py` | `frontend/src/components/MermaidRenderer.tsx` |
| `mermaid_editor.py` | `frontend/src/components/EnhancedDiagramEditor.tsx` |
| `code_editor.py` | `frontend/src/components/CodeEditor.tsx` |
| `export_manager.py` | `backend/services/export_service.py` |
| `version_history.py` | `backend/services/version_service.py` |
| `tech_stack_detector.py` | `backend/utils/tool_detector.py` |
| `test_generator.py` | `backend/services/generation_service.py` |
| `progress_tracker.py` | WebSocket events in frontend |
| `parallel_processing.py` | Async/await in FastAPI |
| `enhanced_api_docs.py` | `frontend/src/components/` |
| `interactive_prototype_editor.py` | `frontend/src/components/InteractivePrototypeEditor.tsx` |
| `visual_diagram_editor.py` | `frontend/src/components/EnhancedDiagramEditor.tsx` |

### Components Still in Use

The following were initially archived but moved back as they're still actively imported:

- `knowledge_graph.py` - Used by `agents/universal_agent.py` (in `components/`)
- `pattern_mining.py` - Used by `agents/universal_agent.py` (in `components/`)
- `local_finetuning.py` - Used by training services (in `components/`)
- `mermaid_html_renderer.py` - Used by diagram generation (in `components/`)
- `mermaid_syntax_corrector.py` - Used by validation (in `components/`)
- `prototype_generator.py` - Used by tests (in `components/`)
- `enhanced_rag.py` - Used by mermaid_html_renderer (in `components/`)

### Fully Retired (Not Used)

These legacy UI modules are no longer referenced by the current FastAPI + React app or tests and can remain deleted:

- `code_editor.py`
- `test_generator.py`
- `export_manager.py`
- `interactive_prototype_editor.py`

## Why Archived?

1. **Streamlit Dependency:** These components import `streamlit` which is no longer used
2. **UI/Logic Separation:** Streamlit mixed UI and business logic; now separated
3. **Better Architecture:** FastAPI + React provides cleaner separation of concerns

## Usage

**DO NOT USE** these components in new development.

For reference only:
- Understand original implementation details
- Port remaining logic to new architecture if needed

## Migration Status

- All critical functionality has been migrated to FastAPI + React
- These files are kept for reference during transition period
- Safe to delete after confirming all features work in new architecture

---

**Archived:** December 2025  
**Original Version:** 2.x (Streamlit)  
**Current Version:** 3.5.2 (FastAPI + React)

