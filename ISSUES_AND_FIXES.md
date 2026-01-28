# Reported Issues - Analysis and Fixes

## Issue #1: Custom Artifact Type Defaulting to Workflows

**Problem**: When generating a custom artifact type, it generates nothing or defaults to workflows.

**Root Cause**: 
- In `/api/generation/stream`, custom artifact types are rejected with `Invalid artifact_type` error
- The code tries to convert custom types to `ArtifactType` enum, which fails

**Fix Applied**:
- Modified `/api/generation/stream` to check for custom artifact types before rejecting
- Allow custom types to pass through as strings

**Status**: ✅ Fixed in `backend/api/generation.py`

---

## Issue #2: Clustering Network Error

**Problem**: Clustering feature has a network error.

**Root Cause**: Need to investigate the clustering endpoint and ML feature service.

**Fix Needed**: 
- Check `/api/analysis/ml-features/project/cluster` endpoint
- Verify MLFeatureEngineer.cluster_features() doesn't make external network calls
- Ensure scikit-learn is available

**Status**: 🔍 Needs investigation

---

## Issue #3: API Key Settings

**Problem**: API key should be settable from settings page.

**Status**: ✅ Should already work - needs verification

---

## Issue #4: Artifacts Not Connected to Meeting Notes

**Problem**: Generated artifacts have no relation to meeting notes in the selected folder.

**Root Cause**:
- Meeting notes are loaded from folder but may not be emphasized enough in prompts
- RAG context may be too generic and not meeting-notes-specific

**Fixes Needed**:
1. Ensure meeting notes are prominently included in prompts
2. Make RAG retrieval meeting-notes-aware
3. Add meeting notes to context building priority

**Status**: 🔧 Needs enhancement

---

## Issue #5: Code Prototype Missing Tests and Integration

**Problem**: Code prototype should include:
- Both code AND tests
- Agentic placement in project structure
- Integration plan

**Current State**: 
- System message already includes instructions for tests and integration plan
- Output format specifies `=== TESTS ===` section

**Fixes Needed**:
- Verify tests are actually generated
- Ensure integration plan is agentic (uses RAG to find correct paths)
- Add validation to ensure tests are present

**Status**: 🔧 Needs verification and enhancement

---

## Issue #6: Visual Prototype Missing Context

**Problem**: Visual prototype should:
- Use codebase context
- Generate prototype based on meeting notes
- Match existing design system

**Current State**:
- System message includes context requirements
- Mentions checking CODE_PROTOTYPE in Project Context

**Fixes Needed**:
- Ensure RAG retrieves UI/UX patterns, design tokens, component libraries
- Verify visual prototype references code prototype when available
- Add validation for design consistency

**Status**: 🔧 Needs enhancement

---

## Issue #7: RAG Not Using All Available Sources

**Problem**: RAG should use all "weapons" available to ensure context is relevant to meeting notes.

**Current State**:
- Context builder includes: RAG, Knowledge Graph, Pattern Mining, ML Features
- But may not be meeting-notes-aware

**Fixes Needed**:
1. Make RAG retrieval meeting-notes-aware (query expansion based on meeting notes)
2. Ensure all context sources (RAG, KG, Patterns, ML) are used
3. Prioritize context that matches meeting notes keywords

**Status**: 🔧 Needs enhancement

---

## Issue #8: Dev Visual Prototype Should Represent Code Prototype

**Problem**: Dev visual prototype should be the visual representation of code prototype.

**Current State**:
- System message mentions checking CODE_PROTOTYPE in Project Context
- But may not actively retrieve it

**Fixes Needed**:
- When generating dev_visual_prototype, actively retrieve and include code_prototype content
- Ensure visual prototype matches code prototype's data structures and logic

**Status**: 🔧 Needs enhancement

---

## Issue #9: GitHub PR Integration

**Problem**: Code prototype should be able to create GitHub PR directly.

**Current State**:
- `GitAgent` exists in `backend/services/git_agent.py`
- Has `apply_prototype_and_push()` method
- Endpoint exists at `/api/git/apply-prototype`

**Fixes Needed**:
- Verify GitAgent works correctly
- Ensure it handles both frontend and backend files
- Test PR creation flow

**Status**: 🔧 Needs verification

---

## Implementation Priority

1. ✅ Fix custom artifact type handling (DONE)
2. 🔍 Investigate clustering network error
3. 🔧 Enhance meeting notes integration
4. 🔧 Enhance code prototype with tests
5. 🔧 Enhance visual prototype with context
6. 🔧 Enhance RAG to be meeting-notes-aware
7. 🔧 Link dev visual prototype to code prototype
8. 🔧 Verify GitHub PR integration
