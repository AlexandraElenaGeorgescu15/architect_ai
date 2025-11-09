# Changelog - Architect.AI

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **Pattern Mining Singleton Detection:** Updated regex patterns to detect both `_instance` (single underscore) and `__instance` (double underscore) singleton patterns. Added additional patterns for explicit None assignments and singleton checks. Test now passes. ✅
- **Automatic Fine-Tuning:** Added automatic background training trigger when batch threshold (50 examples) is met. No longer requires manual execution of `workers/finetuning_worker.py`. Training now starts automatically in background process (non-blocking). ✅
- **Self-Contamination Prevention:** Replaced hardcoded check in `rag/ingest.py` with `_tool_detector.should_exclude_path()`
- **Exception Handling:** Fixed bare `except:` blocks in `agents/universal_agent.py` and `agents/multi_agent_system.py`
- **Directory Structure:** Removed empty nested `architect_ai_cursor_poc/architect_ai_cursor_poc/` directory
- **Test Coverage:** Fixed validation tests to use correct `ValidationResult` interface

### Added
- **Worker Single-Job Mode:** Added `--single-job` argument to `finetuning_worker.py` for automatic training triggers
- **Automatic Background Training:** Added `_start_background_training()` method in `adaptive_learning.py` that spawns background worker process automatically
- **Enhanced Singleton Detection:** Added 6 regex patterns (from 4) to catch more singleton pattern variations
- **Comprehensive Unit Tests:** Added `test_components_coverage.py` with 90%+ coverage for critical components
- **VRAM Management Tests:** Added `test_ollama_vram.py` to verify 12GB RTX 3500 Ada constraints
- **Enhanced Demo HTML:** Updated `workflow_demo.html` with better showcase of unique capabilities
- **Critical Maintainability Checklist:** Added comprehensive checklist to `.cursorrules` for code quality

### Changed
- **Fine-Tuning Workflow:** Changed from manual trigger to automatic background execution when batch threshold is met
- **Pattern Mining:** Improved singleton pattern detection heuristics to match standard Python conventions
- **Documentation:** Consolidated and verified no duplicate documentation exists
- **Cursor Rules:** Enhanced with critical maintainability guidelines, quick fixes, and pre-commit checklist

---

## [3.5.1] - 2025-11-08

### Fixed
- **Unicode Encoding:** Fixed Windows console encoding errors with emoji characters in test outputs
- **Test Files:** Added UTF-8 output handling to `check_setup.py`, `quick_verify.py`, and `run_tests.py`
- **Exception Handling:** Replaced bare `except:` blocks with specific exception types in critical paths
- **File Encoding:** Added explicit `encoding='utf-8'` to all file operations

### Added
- **QUICKSTART.md:** Comprehensive 5-minute getting started guide
- **TROUBLESHOOTING.md:** Detailed troubleshooting guide for common issues
- **CHANGELOG.md:** This file - version history and change tracking
- **Project Health Report:** Comprehensive audit report (`PROJECT_HEALTH_VIABILITY_REPORT.md`)
- **Centralized Configuration:** `config/settings.py` for unified settings management

### Changed
- **Documentation:** Consolidated redundant documentation files
- **.cursorrules:** Updated with maintainability and scalability best practices
- **Test Suite:** Enhanced test coverage and validation

---

## [3.5.0] - 2025-11-05

### Added
- **5-Layer Context System:** RAG + Meeting Notes + Repo Analysis + Knowledge Graph + Pattern Mining
- **Knowledge Graph:** AST parsing (Python) + Regex parsing (TypeScript, C#, Java) → NetworkX graphs
- **Pattern Mining:** Static analysis detecting Singleton, Factory, Observer, Strategy patterns
- **Programmatic Validation:** 8 validators with quality scoring (0-100) and auto-retry
- **Noise Reduction Pipeline:** Preprocessing for RAG queries (comment removal, keyword extraction)
- **Dual Fine-Tuning Pipelines:**
  - Ollama: Automatic feedback collection + manual training trigger
  - HuggingFace: LoRA/QLoRA training with GPU support
- **Adaptive Learning System:** Feedback-driven improvement loop
- **Auto-Ingestion:** File watcher with incremental indexing
- **Tool Self-Detection:** `_tool_detector.py` prevents self-contamination
- **Enhanced RAG:** Hybrid retrieval (vector + BM25) with 18-100 chunks
- **Model Routing:** Automatic fallback from local → cloud providers
- **Parallel Execution:** Artifacts generated via `asyncio.gather()`

### Changed
- **RAG System:** Upgraded to ChromaDB with hybrid search
- **Validation:** Moved from basic checks to comprehensive quality scoring
- **Architecture:** Improved separation of concerns (agents, components, validation)

---

## [3.3.0] - 2025-10-20

### Added
- **Advanced RAG:** Sentence Transformers for embeddings
- **Model Registry:** Track and manage fine-tuned models
- **Ollama Integration:** Local model support
- **Feedback Collection:** UI for collecting user corrections

### Changed
- **Streamlit UI:** Improved layout and user experience
- **Validation:** Added Mermaid syntax checking

---

## [3.0.0] - 2025-10-01

### Added
- **8+ Artifact Types:** ERD, Architecture, API Docs, Code, JIRA, Deployment, Workflows, Prototype
- **RAG System:** Basic ChromaDB integration
- **Validation System:** Basic artifact validation
- **Multi-Provider Support:** OpenAI, Gemini, Groq, Ollama
- **Streamlit UI:** Web-based interface

### Changed
- **Architecture:** Complete rewrite from v2.x
- **Prompts:** Optimized for better output quality

---

## [2.5.0] - 2025-09-15

### Added
- **Prototype Generation:** Angular + .NET code generation
- **JIRA Integration:** Export to JIRA-ready format
- **Version History:** Track artifact versions

### Changed
- **UI:** Redesigned with tabs and better navigation
- **Performance:** Reduced generation time by 40%

---

## [2.0.0] - 2025-08-01

### Added
- **Multiple AI Providers:** OpenAI, Gemini, Groq support
- **RAG Foundation:** Basic retrieval system
- **Artifact Types:** ERD, Architecture, API Docs, JIRA

### Changed
- **Complete Rewrite:** From proof-of-concept to production system
- **Architecture:** Modular component-based design

---

## [1.0.0] - 2025-06-15

### Added
- **Initial Release:** Basic meeting notes → ERD generation
- **OpenAI Integration:** GPT-4 for generation
- **Simple UI:** Command-line interface

---

## Legend

**Types of Changes:**
- `Added` - New features
- `Changed` - Changes to existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Security improvements

**Version Numbering:**
- MAJOR version (X.0.0) - Breaking changes
- MINOR version (0.X.0) - New features (backwards compatible)
- PATCH version (0.0.X) - Bug fixes (backwards compatible)
