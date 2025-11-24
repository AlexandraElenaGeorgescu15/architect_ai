# Architect.AI - System Architecture

## Overview

Architect.AI is being rebuilt as a production-grade FastAPI + React application with clean architecture, optimal performance, and professional UX.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Frontend                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Studio  │  │Intelligence│ │  Canvas  │  │  Chat    │        │
│  │   Page   │  │   Page    │  │  Editor  │  │  Bot    │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│       │              │              │              │             │
│       └──────────────┴──────────────┴──────────────┘             │
│                          │                                        │
│                    ┌─────▼─────┐                                 │
│                    │ API Client │                                 │
│                    │  (Axios)   │                                 │
│                    └─────┬─────┘                                 │
└─────────────────────────┼──────────────────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────▼──────────────────────────────────────┐
│                    FastAPI Backend                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Gateway                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Context │  │Generation│  │ Analysis │  │ Feedback │  │  │
│  │  │ Builder │  │  Service │  │ Service  │  │ Service  │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Core Services                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │   RAG    │  │Knowledge │  │ Pattern  │  │    ML    │  │  │
│  │  │  System  │  │  Graph   │  │  Mining  │  │ Features │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Artifact Plugin System                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Mermaid  │  │   HTML   │  │   Code   │  │    PM    │  │  │
│  │  │Artifacts │  │Artifacts │  │Artifacts │  │Artifacts │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Model Management                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │  Model   │  │  Model   │  │ Training │  │ Dataset  │  │  │
│  │  │  Router  │  │ Registry │  │  System  │  │ Builder  │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────┬──────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│  PostgreSQL  │  │     Redis    │  │   ChromaDB    │
│   (State)    │  │   (Cache)    │  │   (Vector)    │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Backend Architecture

### Directory Structure

```
backend/
├── api/                    # API route handlers
│   ├── context.py          # Context Builder endpoints
│   ├── generation.py        # Generation endpoints
│   ├── analysis.py         # Analysis endpoints
│   ├── feedback.py         # Feedback endpoints
│   └── websocket.py        # WebSocket endpoints
├── core/                   # Core business logic
│   ├── database.py         # Database configuration
│   ├── config.py           # Application settings
│   ├── websocket.py        # WebSocket manager
│   └── artifact_plugin.py  # Artifact plugin system
├── services/               # Business services
│   ├── context_builder.py  # RAG + KG assembly
│   ├── generation.py       # Artifact generation
│   ├── analysis.py          # Pattern mining
│   └── feedback.py         # Feedback collection
├── artifacts/              # Artifact plugins
│   ├── mermaid/            # Mermaid artifact plugins
│   ├── html/               # HTML artifact plugins
│   ├── code/               # Code artifact plugins
│   └── pm/                 # PM artifact plugins
├── models/                 # Data models
│   ├── dto.py              # Pydantic DTOs
│   └── schemas.py          # SQLAlchemy models
├── utils/                  # Utility functions
│   └── tool_detector.py    # Self-contamination prevention
└── main.py                 # FastAPI app entry point
```

### Service Boundaries

#### 1. Context Builder Service
- **Responsibility:** Assemble context from RAG, Knowledge Graph, Pattern Mining, and ML features
- **Input:** Meeting notes, repository ID
- **Output:** Context ID, RAG snippets, Knowledge Graph, Pattern Mining results
- **Dependencies:** RAG system, Knowledge Graph builder, Pattern Miner, ML Feature Engineer

#### 2. Generation Service
- **Responsibility:** Generate artifacts using LLM with validation and multi-agent review
- **Input:** Context ID, artifact type, generation options
- **Output:** Generated artifact with validation score
- **Dependencies:** Artifact plugins, Model Router, Validation Pipeline, Multi-Agent System

#### 3. Analysis Service
- **Responsibility:** Pattern mining and dataset building
- **Input:** Repository ID, analysis type
- **Output:** Pattern reports, training datasets
- **Dependencies:** Pattern Miner, Dataset Builders

#### 4. Feedback Service
- **Responsibility:** Collect user feedback and trigger training
- **Input:** Artifact ID, feedback score, notes
- **Output:** Feedback recorded, training status
- **Dependencies:** Training System, Adaptive Learning Loop

## Frontend Architecture

### Directory Structure

```
frontend/
├── src/
│   ├── pages/              # Page components
│   │   ├── Studio.tsx      # Main generation page
│   │   └── Intelligence.tsx # Model & training page
│   ├── components/         # Reusable components
│   │   ├── layout/         # Layout components
│   │   ├── artifacts/     # Artifact display
│   │   ├── canvas/         # Diagram editor
│   │   └── charts/        # Visualization charts
│   ├── services/           # API clients
│   │   ├── artifactService.ts
│   │   ├── modelService.ts
│   │   └── trainingService.ts
│   ├── stores/            # Zustand stores
│   │   ├── artifactStore.ts
│   │   ├── modelStore.ts
│   │   └── trainingStore.ts
│   ├── hooks/             # Custom hooks
│   │   └── useWebSocket.ts
│   └── App.tsx            # Root component
└── package.json
```

## Data Flow

### Generation Flow

1. **User uploads meeting notes** → React frontend
2. **Frontend calls** `POST /api/context/build` → FastAPI backend
3. **Context Builder** assembles context:
   - RAG retrieval (vector + BM25)
   - Knowledge Graph construction
   - Pattern Mining analysis
   - ML feature extraction
4. **Frontend calls** `POST /api/generation/artifacts` → Generation Service
5. **Generation Service**:
   - Loads artifact plugin
   - Assembles prompt with context
   - Routes to appropriate model
   - Generates artifact
   - Validates artifact
   - Streams progress via WebSocket
6. **Frontend receives** artifact via WebSocket
7. **User provides feedback** → `POST /api/feedback`
8. **Feedback Service** records feedback and triggers training if threshold met

### Training Flow

1. **Feedback collected** → Examples tracked per artifact type
2. **50 examples reached** → Auto-trigger training
3. **Training Service**:
   - Aggregates examples
   - Builds training dataset
   - Triggers LoRA fine-tuning
   - Converts model to Ollama format
   - Updates model routing
4. **Progress streamed** via WebSocket
5. **New model available** → Routing updated automatically

## Technology Stack

### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL (SQLAlchemy)
- **Cache:** Redis
- **Vector DB:** ChromaDB
- **Task Queue:** Celery/Taskiq
- **WebSocket:** FastAPI WebSocket
- **Validation:** Pydantic
- **Logging:** Structured logging

### Frontend
- **Framework:** React + TypeScript
- **Build Tool:** Vite
- **UI Library:** shadcn/ui
- **Styling:** Tailwind CSS
- **State:** Zustand
- **Routing:** React Router
- **HTTP Client:** Axios
- **WebSocket:** socket.io-client
- **Visualization:** React Flow, D3.js, Mermaid.js
- **Editor:** Monaco Editor

## Key Design Patterns

### 1. Plugin Architecture
- Artifact plugins are self-contained modules
- Auto-discovery and registration
- Easy to add new artifact types

### 2. Service-Oriented Architecture
- Clear service boundaries
- Loose coupling between services
- Easy to test and maintain

### 3. Event-Driven Communication
- WebSocket for real-time updates
- Job queues for async processing
- Event sourcing for audit trails

### 4. Caching Strategy
- Redis for session state
- Memory cache for RAG results
- Database cache for model registry

## Security Considerations

1. **Self-Contamination Prevention**
   - Tool detector excludes Architect.AI code
   - Verified in all ingestion paths

2. **Input Validation**
   - Pydantic schemas for all inputs
   - XSS protection for user content
   - Path traversal prevention

3. **Authentication**
   - JWT tokens for API access
   - API keys for service-to-service
   - WebSocket authentication

4. **Rate Limiting**
   - Per-user rate limits
   - Per-endpoint rate limits
   - DDoS protection

## Performance Optimizations

1. **Caching**
   - RAG results cached
   - Knowledge Graph cached
   - Model registry cached

2. **Async Processing**
   - Long-running jobs in queue
   - WebSocket for streaming
   - Non-blocking I/O

3. **Database Optimization**
   - Indexes on frequently queried fields
   - Eager loading for relationships
   - Connection pooling

4. **Frontend Optimization**
   - Code splitting
   - Lazy loading
   - Virtual scrolling
   - React.memo for expensive components

## Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│              Load Balancer (Nginx)              │
└───────────────┬─────────────────────────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
┌───▼────┐            ┌─────▼────┐
│ React  │            │ FastAPI  │
│  App   │            │ Backend  │
│(Static)│            │(Gunicorn)│
└────────┘            └─────┬─────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐        ┌────▼────┐       ┌────▼────┐
   │PostgreSQL│       │  Redis  │       │ ChromaDB │
   └─────────┘        └─────────┘       └─────────┘
```

## Migration Strategy

1. **Phase 0:** Complete audit (✅ Done)
2. **Phase 1:** Backend architecture design (🚧 In Progress)
3. **Phase 2:** Backend development (Days 6-25)
4. **Phase 3:** Frontend development (Days 26-40)
5. **Phase 4:** Integration & testing (Days 41-50)

## References

- **Design Blueprint:** `outputs/design.md`
- **Implementation Plan:** `documentation/ULTRA_DETAILED_PLAN.md`
- **API Documentation:** `documentation/API.md` (to be created)
- **Day 1 Audit:** `documentation/PHASE0_DAY1_AUDIT.md`
- **Day 2 Audit:** `documentation/PHASE0_DAY2_AUDIT.md`



