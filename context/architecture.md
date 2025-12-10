# Architect.AI - System Architecture

## Overview

Architect.AI is a production-grade AI-powered software architecture assistant built with FastAPI (backend) and React + TypeScript (frontend).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      React Frontend (Port 3000)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Studio  │  │Intelligence│ │  Canvas  │  │Floating │        │
│  │   Page   │  │   Page    │  │  Editor  │  │  Chat   │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘        │
│       └─────────────┴─────────────┴─────────────┘              │
│                          │                                      │
│                    ┌─────▼─────┐                               │
│                    │ API Client │                               │
│                    │  (Axios)   │                               │
│                    └─────┬─────┘                               │
└─────────────────────────┼───────────────────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend (Port 8000)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Layer (32 endpoints)               │  │
│  │  /api/context  /api/generation  /api/analysis  /ws/...   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Services Layer                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Context  │  │Generation│  │ Analysis │  │ Feedback │  │  │
│  │  │ Builder  │  │ Service  │  │ Service  │  │ Service  │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               Intelligence Layer                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │   RAG    │  │Knowledge │  │ Pattern  │  │Universal │  │  │
│  │  │Retriever │  │  Graph   │  │  Mining  │  │ Context  │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                Model Management                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │  Model   │  │  Model   │  │ Training │  │ Dataset  │  │  │
│  │  │  Router  │  │ Registry │  │  System  │  │ Builder  │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│    SQLite    │  │   ChromaDB   │  │    Ollama    │
│   (State)    │  │   (Vector)   │  │   (Local)    │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Technology Stack

### Backend
- **Framework:** FastAPI (async Python)
- **Database:** SQLite with SQLAlchemy ORM
- **Vector Store:** ChromaDB
- **Knowledge Graph:** NetworkX
- **Authentication:** JWT + API Keys
- **WebSocket:** FastAPI WebSocket

### Frontend
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **State:** Zustand
- **Routing:** React Router v6
- **HTTP Client:** Axios
- **Diagrams:** Mermaid.js, React Flow

### AI/ML
- **Local Models:** Ollama (DeepSeek, Llama, Mistral)
- **Cloud Models:** Gemini, GPT-4, Groq, Claude
- **Embeddings:** Sentence Transformers
- **Fine-tuning:** LoRA/QLoRA with PEFT

## Key Components

### 1. Context Builder
Assembles comprehensive context for artifact generation:
- RAG retrieval (vector + BM25 hybrid search)
- Knowledge Graph (AST parsing, component relationships)
- Pattern Mining (design patterns, code smells, security issues)
- Meeting notes integration

### 2. Generation Service
Generates artifacts using multi-model routing:
- 50+ artifact types (ERD, architecture, code, docs, PM)
- Automatic validation and quality scoring
- Version tracking and comparison
- Streaming progress via WebSocket

### 3. Model Management
Handles AI model selection and training:
- Smart routing based on artifact type
- Fine-tuned model prioritization
- Automatic fallback to cloud models
- Training job management

### 4. RAG System
Retrieval-Augmented Generation:
- Incremental indexing with file watching
- Hybrid search (vector similarity + BM25)
- Self-contamination prevention
- Chunk optimization

## Data Flow

1. **User uploads meeting notes** → React frontend
2. **Frontend calls** `POST /api/context/build`
3. **Context Builder** assembles 5-layer context
4. **Frontend calls** `POST /api/generation/artifacts`
5. **Generation Service** routes to appropriate model
6. **Progress streamed** via WebSocket
7. **User provides feedback** → Training pipeline

## Version History

- **v3.5.2** (Current) - Bug fixes, onboarding tour
- **v3.5.0** - Migration to FastAPI + React
- **v3.0.0** - RAG system, 50+ artifact types
- **v2.0.0** - Streamlit web interface (archived)
- **v1.0.0** - Initial CLI release

