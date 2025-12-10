# Retrieved Context

This file contains RAG-retrieved context for the current session.

## Purpose
- Primary evidence source for AI-assisted design and code generation
- Updated dynamically during context building
- Contains relevant code snippets, documentation, and patterns from the indexed codebase

## Usage
When generating artifacts or answering questions:
1. This file is populated with relevant context from RAG retrieval
2. Cite snippets by file path in generated documents
3. If key information is missing, list assumptions clearly

## Current Context
*No context retrieved yet. Build context using the Context Builder in the UI.*

---

## How Context is Built

1. **RAG Retrieval**: Vector similarity + BM25 hybrid search
2. **Knowledge Graph**: Component relationships and dependencies
3. **Pattern Mining**: Design patterns, code smells, security issues
4. **Meeting Notes**: User requirements and specifications

## Context Freshness
- Context is rebuilt when meeting notes change
- Manual refresh available via API: `POST /api/context/build`
- Auto-refresh on file changes (if watchers enabled)

