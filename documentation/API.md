# Architect.AI API Documentation

Complete API reference for the FastAPI backend service.

## Base URL

```
http://localhost:8000
```

## Authentication

### JWT Bearer Token

1. Login to get access token:
```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=user&password=pass
```

2. Use token in Authorization header:
```http
Authorization: Bearer <access_token>
```

### API Key

```http
X-API-Key: <api_key>
```

## Endpoints

### Authentication

#### Login
```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

Response:
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Generate API Key
```http
POST /api/auth/api-key
Authorization: Bearer <token>

Response:
{
  "key": "sk-architectai-...",
  "name": "default",
  "user_id": "user",
  "created_at": "2024-01-01T00:00:00"
}
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer <token>

Response:
{
  "username": "user",
  "scopes": ["user"]
}
```

---

### Context Builder

#### Build Context
```http
POST /api/context/build
Authorization: Bearer <token>
Content-Type: application/json

{
  "meeting_notes": "Create a user authentication system...",
  "repo_id": "optional-repo-id",
  "include_rag": true,
  "include_kg": true,
  "include_patterns": true,
  "include_ml_features": false,
  "max_rag_chunks": 18,
  "kg_depth": 2
}

Response:
{
  "success": true,
  "context_id": "uuid-here",
  "assembled_context": "Full context string...",
  "sources": {
    "rag": [...],
    "knowledge_graph": {...},
    "patterns": {...}
  },
  "from_cache": false,
  "metadata": {...}
}
```

#### Get Context Stats
```http
GET /api/context/stats
Authorization: Bearer <token>

Response:
{
  "success": true,
  "stats": {
    "total_builds": 100,
    "cache_hits": 50,
    "avg_build_time_ms": 1500
  }
}
```

#### Get Context by ID
```http
GET /api/context/{context_id}
Authorization: Bearer <token>

Response: Same as Build Context response
```

---

### Generation

#### Generate Artifact (Non-Streaming)
```http
POST /api/generation/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "context_id": "uuid-from-context-build",
  "artifact_type": "mermaid_erd",
  "options": {
    "max_retries": 3,
    "use_validation": true,
    "use_multi_agent": false,
    "temperature": 0.7
  }
}

Response:
{
  "job_id": "uuid-here",
  "status": "pending",
  "message": "Generation for 'mermaid_erd' started in background."
}
```

#### Generate Artifact (Streaming)
```http
POST /api/generation/stream
Authorization: Bearer <token>
Content-Type: application/json

Same request body as non-streaming

Response: Server-Sent Events (SSE) stream
data: {"status": "in_progress", "progress": 25, ...}
data: {"status": "in_progress", "progress": 50, ...}
data: {"status": "completed", "progress": 100, "artifact": {...}}
```

#### Get Generation Job Status
```http
GET /api/generation/jobs/{job_id}
Authorization: Bearer <token>

Response:
{
  "job_id": "uuid-here",
  "status": "completed",
  "artifact": {
    "id": "artifact-id",
    "artifact_type": "mermaid_erd",
    "content": "erDiagram\n...",
    "validation": {
      "score": 85.0,
      "is_valid": true,
      ...
    },
    "model_used": "llama3",
    "generated_at": "2024-01-01T00:00:00"
  },
  "error": null
}
```

#### List Generation Jobs
```http
GET /api/generation/jobs
Authorization: Bearer <token>

Response:
[
  {
    "job_id": "uuid-1",
    "status": "completed",
    ...
  },
  {
    "job_id": "uuid-2",
    "status": "in_progress",
    ...
  }
]
```

#### Cancel Generation Job
```http
POST /api/generation/jobs/{job_id}/cancel
Authorization: Bearer <token>

Response:
{
  "message": "Job {job_id} cancelled."
}
```

---

### Validation

#### Validate Single Artifact
```http
POST /api/validation/validate
Authorization: Bearer <token>
Content-Type: application/json

{
  "artifact_type": "mermaid_erd",
  "content": "erDiagram\nUser ||--o{ Post",
  "context": {
    "meeting_notes": "Create a blog system..."
  }
}

Response:
{
  "success": true,
  "validation_result": {
    "score": 85.0,
    "is_valid": true,
    "validators": {
      "syntax": {"passed": true},
      "relevance": {"passed": true, "score": 0.9}
    },
    "errors": [],
    "warnings": ["Missing relationship labels"]
  }
}
```

#### Validate Batch
```http
POST /api/validation/validate-batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "artifacts": [
    {
      "artifact_type": "mermaid_erd",
      "content": "..."
    },
    {
      "artifact_type": "mermaid_architecture",
      "content": "..."
    }
  ]
}

Response:
{
  "success": true,
  "validation_results": [
    {...},
    {...}
  ]
}
```

#### Get Validation Stats
```http
GET /api/validation/stats
Authorization: Bearer <token>

Response:
{
  "success": true,
  "stats": {
    "total_validations": 1000,
    "average_score": 82.5,
    "pass_rate": 0.95
  }
}
```

---

### Feedback

#### Submit Feedback
```http
POST /api/feedback/
Authorization: Bearer <token>
Content-Type: application/json

{
  "artifact_id": "artifact-123",
  "score": 85.0,
  "notes": "Good ERD but missing relationships",
  "feedback_type": "correction",
  "corrected_content": "erDiagram\n..."
}

Response:
{
  "recorded": true,
  "examples_collected": 50,
  "training_triggered": false,
  "message": "Feedback recorded successfully"
}
```

#### Get Feedback History
```http
GET /api/feedback/history?artifact_id=artifact-123&limit=100
Authorization: Bearer <token>

Response:
[
  {
    "artifact_id": "artifact-123",
    "artifact_type": "mermaid_erd",
    "feedback_type": "positive",
    "validation_score": 85.0,
    "reward_signal": 0.8,
    "timestamp": "2024-01-01T00:00:00"
  },
  ...
]
```

#### Get Feedback Stats
```http
GET /api/feedback/stats
Authorization: Bearer <token>

Response:
{
  "total_feedback_events": 100,
  "average_validation_score": 82.5,
  "average_reward_signal": 0.75,
  "feedback_by_artifact_type": {
    "mermaid_erd": 50,
    "mermaid_architecture": 30,
    ...
  },
  "training_batches_created": 5,
  "adaptive_learning_enabled": true
}
```

#### Check Training Readiness
```http
GET /api/feedback/training-ready?artifact_type=mermaid_erd
Authorization: Bearer <token>

Response:
{
  "ready": true,
  "reason": "50+ examples collected",
  "examples_count": 52
}
```

---

### RAG

#### Index Directory
```http
POST /api/rag/index
Authorization: Bearer <token>
Content-Type: application/json

{
  "directory_path": "/path/to/repo"
}

Response:
{
  "success": true,
  "message": "Indexing of '/path/to/repo' started in background."
}
```

#### Search RAG
```http
POST /api/rag/search
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "user authentication login",
  "k": 10,
  "metadata_filter": {"file_type": "python"},
  "force_refresh": false
}

Response:
{
  "success": true,
  "context": "Retrieved context snippets...",
  "num_results": 10,
  "from_cache": false
}
```

#### Watch Directory
```http
POST /api/rag/watch
Authorization: Bearer <token>
Content-Type: application/json

{
  "directory_path": "/path/to/repo"
}

Response:
{
  "success": true,
  "message": "Watching '/path/to/repo' for changes."
}
```

#### Invalidate Cache
```http
POST /api/rag/cache/invalidate
Authorization: Bearer <token>
Content-Type: application/json

{
  "meeting_notes_query": "optional query to invalidate"
}

Response:
{
  "success": true,
  "message": "5 cache entries invalidated."
}
```

#### Get RAG Stats
```http
GET /api/rag/index/stats
Authorization: Bearer <token>

Response:
{
  "success": true,
  "stats": {
    "total_documents": 1000,
    "index_size_mb": 50.5
  }
}
```

---

### Knowledge Graph

#### Build Knowledge Graph
```http
POST /api/knowledge-graph/build
Authorization: Bearer <token>
Content-Type: application/json

{
  "directory_path": "/path/to/repo"
}

Response:
{
  "job_id": "uuid-here",
  "status": "pending",
  "message": "Knowledge graph build for '/path/to/repo' started in background."
}
```

#### Get KG Stats
```http
GET /api/knowledge-graph/stats
Authorization: Bearer <token>

Response:
{
  "success": true,
  "stats": {
    "nodes": 500,
    "edges": 1200,
    "components": 200
  }
}
```

#### Get Full Graph
```http
GET /api/knowledge-graph/graph
Authorization: Bearer <token>

Response:
{
  "nodes": [
    {
      "id": "UserModel",
      "label": "UserModel",
      "type": "class",
      "properties": {...}
    },
    ...
  ],
  "edges": [
    {
      "source": "UserModel",
      "target": "PostModel",
      "relationship": "has_many",
      "weight": 1.0
    },
    ...
  ],
  "metadata": {...}
}
```

#### Find Shortest Path
```http
POST /api/knowledge-graph/path
Authorization: Bearer <token>
Content-Type: application/json

{
  "source": "UserModel",
  "target": "PostModel"
}

Response:
{
  "source": "UserModel",
  "target": "PostModel",
  "path": ["UserModel", "UserPostRelation", "PostModel"]
}
```

#### Calculate Centrality
```http
POST /api/knowledge-graph/centrality
Authorization: Bearer <token>
Content-Type: application/json

{
  "metric": "degree"
}

Response:
{
  "metric": "degree",
  "centrality_scores": {
    "UserModel": 0.5,
    "PostModel": 0.3,
    ...
  }
}
```

---

### Pattern Mining

#### Start Pattern Mining
```http
POST /api/analysis/patterns/
Authorization: Bearer <token>
Content-Type: application/json

{
  "repo_id": "/path/to/repo",
  "detectors": ["singleton", "factory"]
}

Response:
{
  "job_id": "uuid-here",
  "status": "pending",
  "message": "Pattern mining for '/path/to/repo' started in background."
}
```

#### Get Pattern Mining Results
```http
GET /api/analysis/patterns/{job_id}
Authorization: Bearer <token>

Response:
{
  "job_id": "uuid-here",
  "status": "completed",
  "report": {
    "patterns_detected": [
      {
        "pattern": "Singleton",
        "file": "config.py",
        "line": 10
      }
    ],
    "code_smells": [...],
    "security_issues": [...],
    "statistics": {...}
  }
}
```

---

### ML Features

#### Extract Code Features
```http
POST /api/analysis/ml-features/extract-code
Authorization: Bearer <token>
Content-Type: application/json

{
  "code_samples": [
    "def function(): ...",
    "class MyClass: ..."
  ]
}

Response:
{
  "success": true,
  "features": [
    {
      "line_count": 50,
      "complexity": 15,
      "dependencies": 5,
      ...
    },
    ...
  ]
}
```

#### Cluster Features
```http
POST /api/analysis/ml-features/cluster
Authorization: Bearer <token>
Content-Type: application/json

{
  "features": [{...}, {...}],
  "n_clusters": 5,
  "method": "kmeans"
}

Response:
{
  "success": true,
  "cluster_labels": [0, 1, 0, 2, ...],
  "n_clusters": 5,
  "silhouette_score": 0.75,
  "cluster_examples": {
    "0": ["example1", "example2"],
    ...
  }
}
```

---

## WebSocket API

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/job-123?token=<jwt-token>');
```

### Events

#### Generation Progress
```json
{
  "type": "generation.progress",
  "data": {
    "status": "in_progress",
    "progress": 50,
    "message": "Generating ERD...",
    "timestamp": "2024-01-01T00:00:00"
  }
}
```

#### Generation Complete
```json
{
  "type": "generation.complete",
  "data": {
    "status": "completed",
    "progress": 100,
    "artifact": {...},
    "timestamp": "2024-01-01T00:00:00"
  }
}
```

#### Training Progress
```json
{
  "type": "training.progress",
  "data": {
    "status": "training",
    "progress": 75,
    "epoch": 5,
    "loss": 0.15,
    "timestamp": "2024-01-01T00:00:00"
  }
}
```

### Client Messages

#### Ping
```json
{
  "type": "ping"
}
```

#### Subscribe
```json
{
  "type": "subscribe",
  "rooms": ["job-123", "job-456"]
}
```

#### Unsubscribe
```json
{
  "type": "unsubscribe",
  "rooms": ["job-123"]
}
```

See `documentation/WEBSOCKET_API.md` for full WebSocket documentation.

---

## Error Responses

All errors follow this format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "type": "ExceptionClassName",
  "request_id": "uuid-here",
  "timestamp": "2024-01-01T00:00:00"
}
```

### Common Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error

---

## Rate Limiting

Default rate limits:
- Authentication: 5 requests/minute
- Generation: 5 requests/minute
- RAG Search: 10 requests/minute
- Validation: 10 requests/minute
- Other endpoints: 30 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 1234567890
```

---

## Pagination

List endpoints support pagination:

```http
GET /api/generation/jobs?page=1&page_size=20
```

Response includes pagination metadata:
```json
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 100,
  "total_pages": 5
}
```

---

## Artifact Types

Supported artifact types:

- `mermaid_erd` - Entity-Relationship Diagram
- `mermaid_architecture` - Architecture Diagram
- `mermaid_sequence` - Sequence Diagram
- `mermaid_class` - Class Diagram
- `mermaid_state` - State Diagram
- `mermaid_flowchart` - Flowchart
- `mermaid_data_flow` - Data Flow Diagram
- `mermaid_user_flow` - User Flow Diagram
- `mermaid_component` - Component Diagram
- `mermaid_gantt` - Gantt Chart
- `mermaid_pie` - Pie Chart
- `mermaid_journey` - User Journey
- `mermaid_mindmap` - Mind Map
- `html_erd` - HTML ERD
- `html_architecture` - HTML Architecture
- `html_sequence` - HTML Sequence
- `code_prototype` - Code Prototype
- `api_docs` - API Documentation
- `jira` - Jira Tasks
- `workflows` - Workflows
- `backlog` - Backlog
- `personas` - Personas
- `estimations` - Estimations
- `feature_scoring` - Feature Scoring

---

## Examples

### Complete Workflow

```bash
# 1. Login
TOKEN=$(curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=pass" | jq -r '.access_token')

# 2. Build Context
CONTEXT_ID=$(curl -X POST "http://localhost:8000/api/context/build" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_notes": "Create a blog system with users and posts",
    "include_rag": true
  }' | jq -r '.context_id')

# 3. Generate Artifact
JOB_ID=$(curl -X POST "http://localhost:8000/api/generation/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"context_id\": \"$CONTEXT_ID\",
    \"artifact_type\": \"mermaid_erd\"
  }" | jq -r '.job_id')

# 4. Check Status
curl -X GET "http://localhost:8000/api/generation/jobs/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN"

# 5. Submit Feedback
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id": "artifact-123",
    "score": 85.0,
    "feedback_type": "positive"
  }'
```

---

For interactive API exploration, visit http://localhost:8000/api/docs
