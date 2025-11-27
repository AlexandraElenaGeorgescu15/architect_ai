# Changelog

All notable changes to Architect.AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Unified model selection system - any Ollama model can work with any artifact type
- Automatic fine-tuned model prioritization - fine-tuned models always tried first
- Fine-tuning worker now actually creates Ollama models (not just logs)
- Model auto-refresh in UI (every 30 seconds) to catch newly created models
- Model download with streaming progress and status updates
- Automatic routing updates when fine-tuned models are created

### Fixed
- Fine-tuning integration - models now properly registered and appear in UI
- Model selection priority - fine-tuned models always checked first
- Model registry synchronization - fine-tuned models loaded on startup
- Model download registration - models appear immediately after download
- Artifact-to-model mapping - fine-tuned models automatically mapped to artifact types
- Model routing consistency - unified system across all services

### Changed
- Enhanced onboarding tour with detailed descriptions and centered modal with overlay
- Model selection now uses unified priority system (fine-tuned → routing → base → any model)
- Fine-tuning worker creates actual Ollama models using Modelfile approach
- ModelService automatically prioritizes fine-tuned models on startup
- Cleaned up redundant documentation files (removed 10+ temporary status/fix/implementation docs)

---

## [3.5.2] - 2025-11-24

### Added
- Interactive onboarding tour for new users
- Meeting notes move/rename/delete operations
- Code with tests editor for prototype artifacts
- Interactive prototype editor with live preview
- Enhanced diagram editor with Mermaid rendering
- Floating AI chat assistant
- Frontend troubleshooting documentation

### Fixed
- Frontend-backend connection issues (Vite proxy configuration)
- Knowledge Graph and Pattern Mining cache overwrite bug
- Pattern Mining API endpoint routing conflict (404 error)
- Model availability detection for Groq and OpenAI models
- Synthetic data stats endpoint error handling
- React Router v6 deprecation warnings
- WebSocket connection handling
- UTF-8 encoding for all file operations

### Changed
- Improved Knowledge Graph to accumulate data from multiple directories
- Enhanced Pattern Mining to combine results before caching
- Updated ModelService to correctly detect xai_api_key for Groq models
- Refactored meeting notes API with full CRUD operations

### Removed
- Deprecated diagram editor (replaced with enhanced version)
- 58+ temporary documentation files (fixes, status, audit files)
- All archived documentation in documentation/archive/

---

## [3.5.1] - 2025-11-22

### Fixed
- Backend startup errors with finetuning pool initialization
- Dark mode contrast issues across all components
- Header color consistency in dark mode
- Intelligence page data loading

### Changed
- Improved error handling for missing API keys
- Enhanced VRAM management for Ollama models

---

## [3.5.0] - 2025-11-20

### Added
- React + TypeScript frontend (replaced Streamlit)
- FastAPI async backend
- Real-time WebSocket updates
- Meeting notes management system with AI folder suggestions
- Bulk artifact generation
- Template gallery
- Knowledge Graph visualization
- Pattern Mining results viewer
- Model routing configuration UI
- Training job management UI
- Premium dark/light mode with deep navy theme

### Changed
- Complete UI/UX overhaul with modern design
- Migrated from Streamlit to React
- Improved artifact generation speed (3x faster)
- Enhanced RAG retrieval with hybrid search

### Removed
- Legacy Streamlit app (archived in archive/legacy_streamlit/)

---

## [3.4.0] - 2025-11-15

### Added
- Synthetic dataset generation for bootstrapping training
- Enhanced adaptive learning with curriculum learning
- Hard negative mining for better training
- Hyperparameter optimization (Optuna integration)
- Data augmentation for training examples
- Performance tracking and metrics dashboard

### Changed
- Improved fine-tuning quality with advanced reward calculation
- Enhanced similarity metrics with semantic embeddings
- Better batch management for training

---

## [3.3.0] - 2025-11-10

### Added
- Local fine-tuning with LoRA/QLoRA
- Feedback collection system (thumbs up/down)
- Finetuning dataset builder
- Ollama integration for local model training
- Training job persistence and history

### Changed
- Improved artifact quality with validation pipeline
- Enhanced code prototype generation with test coverage

---

## [3.2.0] - 2025-11-05

### Added
- Knowledge Graph with AST parsing and NetworkX
- Pattern Mining with static analysis
- Design pattern detection
- Code smell detection
- Security issue detection
- Self-contamination prevention system (_tool_detector.py)

### Changed
- Enhanced RAG with 5-layer context system
- Improved artifact generation accuracy

---

## [3.1.0] - 2025-11-01

### Added
- Multi-model support (Gemini, GPT-4, Groq, Claude, Ollama)
- Model routing per artifact type
- Fallback model configuration
- Model registry and status tracking

### Changed
- Improved model selection logic
- Better error handling for API failures

---

## [3.0.0] - 2025-10-25

### Added
- 50+ artifact types (ERD, architecture, code, docs, PM artifacts)
- RAG system with ChromaDB
- Incremental indexing with file change watching
- Auto-ingestion on startup
- Hybrid search (vector + BM25)

### Changed
- Complete rewrite of generation pipeline
- Improved prompt engineering
- Better context management

---

## [2.0.0] - 2025-10-15

### Added
- Streamlit web interface
- SQLite database for persistence
- Artifact versioning and history
- Export functionality (Markdown, JSON, HTML)

### Changed
- Migrated from CLI to web app
- Improved user experience

---

## [1.0.0] - 2025-10-01

### Added
- Initial release
- Basic ERD generation
- Architecture diagram generation
- Command-line interface
- OpenAI GPT-4 integration

---

## Release Types

- **Major** (X.0.0): Breaking changes, major new features
- **Minor** (x.X.0): New features, backward compatible
- **Patch** (x.x.X): Bug fixes, improvements

---

## Links

- [Unreleased]: Compare latest commits
- [3.5.2]: https://github.com/your-repo/releases/tag/v3.5.2
- [3.5.1]: https://github.com/your-repo/releases/tag/v3.5.1
- [3.5.0]: https://github.com/your-repo/releases/tag/v3.5.0

---

**Note:** Dates are in YYYY-MM-DD format (ISO 8601)

