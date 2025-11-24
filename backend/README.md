# Architect.AI Backend API

FastAPI backend service for interactive architecture visualization and artifact generation.

## Overview

The backend provides a RESTful API and WebSocket interface for:
- **Context Building**: RAG retrieval, Knowledge Graph analysis, Pattern Mining, ML Feature extraction
- **Artifact Generation**: ERD, Architecture diagrams, Sequence diagrams, Code prototypes, API docs, PM artifacts
- **Validation**: Quality scoring and validation for generated artifacts
- **Feedback**: User feedback collection and adaptive learning integration
- **Model Management**: Model registry, routing, and fine-tuning

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL (optional, SQLite by default)
- Ollama (for local model inference)
- ChromaDB (for RAG indexing)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database (if using SQLAlchemy)
alembic upgrade head

# Run the server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

See `.env.example` for all configuration options. Key variables:

- `DATABASE_URL`: Database connection string
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `RAG_INDEX_PATH`: Path to ChromaDB index
- `OLLAMA_BASE_URL`: Ollama server URL
- `CORS_ORIGINS`: Allowed CORS origins

## API Documentation

### Interactive Docs

Once the server is running:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

### Authentication

The API supports two authentication methods:

1. **JWT Bearer Token** (recommended)
   ```bash
   # Login
   curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user&password=pass"
   
   # Use token
   curl -X GET "http://localhost:8000/api/context/stats" \
     -H "Authorization: Bearer <token>"
   ```

2. **API Key**
   ```bash
   curl -X GET "http://localhost:8000/api/context/stats" \
     -H "X-API-Key: <api-key>"
   ```

### Core Endpoints

#### Context Builder (`/api/context`)

- `POST /api/context/build` - Build comprehensive context from meeting notes
- `GET /api/context/stats` - Get context builder statistics
- `GET /api/context/{context_id}` - Get previously built context

#### Generation (`/api/generation`)

- `POST /api/generation/generate` - Generate artifact (non-streaming)
- `POST /api/generation/stream` - Generate artifact with SSE streaming
- `GET /api/generation/jobs/{job_id}` - Get generation job status
- `GET /api/generation/jobs` - List all generation jobs
- `POST /api/generation/jobs/{job_id}/cancel` - Cancel generation job

#### Validation (`/api/validation`)

- `POST /api/validation/validate` - Validate single artifact
- `POST /api/validation/validate-batch` - Validate multiple artifacts
- `GET /api/validation/stats` - Get validation statistics

#### Feedback (`/api/feedback`)

- `POST /api/feedback/` - Submit feedback on artifact
- `GET /api/feedback/history` - Get feedback history
- `GET /api/feedback/stats` - Get feedback statistics
- `GET /api/feedback/training-ready` - Check training readiness

#### RAG (`/api/rag`)

- `POST /api/rag/index` - Index directory for RAG
- `POST /api/rag/search` - Perform RAG search
- `POST /api/rag/watch` - Start watching directory for changes
- `POST /api/rag/cache/invalidate` - Invalidate RAG cache
- `GET /api/rag/index/stats` - Get RAG index statistics

#### Knowledge Graph (`/api/knowledge-graph`)

- `POST /api/knowledge-graph/build` - Build knowledge graph
- `GET /api/knowledge-graph/stats` - Get KG statistics
- `GET /api/knowledge-graph/graph` - Get full knowledge graph
- `POST /api/knowledge-graph/path` - Find shortest path
- `POST /api/knowledge-graph/centrality` - Calculate centrality

#### Pattern Mining (`/api/analysis/patterns`)

- `POST /api/analysis/patterns/` - Start pattern mining analysis
- `GET /api/analysis/patterns/{job_id}` - Get analysis results
- `GET /api/analysis/patterns/` - List all jobs
- `POST /api/analysis/patterns/analyze-file` - Analyze single file

#### ML Features (`/api/analysis/ml-features`)

- `POST /api/analysis/ml-features/extract-code` - Extract code features
- `POST /api/analysis/ml-features/extract-diagram` - Extract diagram features
- `POST /api/analysis/ml-features/cluster` - Cluster features
- `POST /api/analysis/ml-features/reduce-dimensions` - Reduce dimensions
- `POST /api/analysis/ml-features/feature-importance` - Analyze importance

### WebSocket API

Connect to `/ws/{room_id}` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/job-123?token=<jwt-token>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data.data);
};
```

**Event Types:**
- `generation.progress` - Generation progress update
- `generation.chunk` - Streaming content chunk
- `generation.complete` - Generation completed
- `generation.error` - Generation error
- `training.progress` - Training progress update
- `training.complete` - Training completed

See `documentation/WEBSOCKET_API.md` for full documentation.

## Service Architecture

### Services

- **ContextBuilder** (`backend/services/context_builder.py`)
  - Combines RAG, Knowledge Graph, Pattern Mining, ML Features
  - Parallel context building from multiple sources
  - Context assembly and ranking

- **GenerationService** (`backend/services/generation_service.py`)
  - Artifact generation with streaming support
  - Multi-model support with fallback
  - Validation integration
  - Retry logic

- **ValidationService** (`backend/services/validation_service.py`)
  - Artifact-specific validation
  - Quality scoring (0-100)
  - Multiple validators per artifact type
  - Batch processing

- **FeedbackService** (`backend/services/feedback_service.py`)
  - User feedback collection
  - Quality gating
  - Training batch creation
  - Adaptive learning integration

- **RAGRetriever** (`backend/services/rag_retriever.py`)
  - Hybrid search (BM25 + vector)
  - Reranking algorithm
  - Query logging

- **RAGIngester** (`backend/services/rag_ingester.py`)
  - Incremental indexing
  - File system watching
  - SHA1 hash-based change detection

- **KnowledgeGraphBuilder** (`backend/services/knowledge_graph.py`)
  - AST parsing for Python
  - NetworkX graph construction
  - Graph query methods

- **PatternMiner** (`backend/services/pattern_mining.py`)
  - Design pattern detection
  - Code smell detection
  - Security issue detection

- **MLFeatureEngineer** (`backend/services/ml_features.py`)
  - Code/diagram feature extraction
  - Clustering analysis
  - Dimensionality reduction
  - Feature importance analysis

### Core Components

- **Authentication** (`backend/core/auth.py`)
  - JWT token creation/verification
  - API key authentication
  - Password hashing

- **WebSocket Manager** (`backend/core/websocket.py`)
  - Connection management
  - Room-based broadcasting
  - Heartbeat mechanism
  - Event emission

- **Middleware** (`backend/core/middleware.py`)
  - Request ID tracking
  - Timing middleware
  - Structured logging
  - Rate limiting

- **Database** (`backend/core/database.py`)
  - SQLAlchemy ORM
  - Connection pooling
  - Migration support

## Development

### Running Tests

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Run specific test file
pytest backend/tests/test_integration.py -v
```

### Code Structure

```
backend/
├── api/              # FastAPI route handlers
├── core/             # Core infrastructure (auth, websocket, middleware)
├── models/           # Pydantic DTOs and SQLAlchemy models
├── services/         # Business logic services
├── utils/            # Utility functions
├── tests/            # Integration tests
└── main.py           # FastAPI application entry point
```

### Adding New Services

1. Create service class in `backend/services/`
2. Create API router in `backend/api/`
3. Add DTOs to `backend/models/dto.py`
4. Register router in `backend/main.py`
5. Write tests in `backend/tests/`

## Deployment

### Docker

```bash
# Build image
docker build -t architect-ai-backend .

# Run container
docker run -p 8000:8000 --env-file .env architect-ai-backend
```

### Docker Compose

```bash
docker-compose -f docker-compose.backend.yml up -d
```

### Production Considerations

- Use PostgreSQL instead of SQLite
- Set up Redis for caching
- Configure proper CORS origins
- Use environment variables for secrets
- Set up monitoring and logging
- Enable rate limiting
- Use HTTPS/TLS

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure parent directory is in Python path
2. **Database Errors**: Check DATABASE_URL and run migrations
3. **RAG Errors**: Ensure ChromaDB index exists and is accessible
4. **Ollama Errors**: Check OLLAMA_BASE_URL and model availability
5. **WebSocket Errors**: Check authentication token and room ID

### Logging

Logs are structured JSON format. Set `LOG_LEVEL=DEBUG` for verbose logging.

## License

MIT License - see LICENSE file for details.



