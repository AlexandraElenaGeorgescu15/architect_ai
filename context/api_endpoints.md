# Architect.AI - API Endpoints

Base URL: `http://localhost:8000`

## Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with system status |
| GET | `/api/health` | Health check (alias) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/metrics/stats` | Metrics in JSON format |

## Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login with username/password |
| POST | `/api/auth/api-key` | Generate API key |
| GET | `/api/auth/me` | Get current user info |

## Context Building

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/context/build` | Build context from meeting notes |
| GET | `/api/context/{context_id}` | Get context by ID |
| GET | `/api/context/status/{context_id}` | Get context build status |

## Artifact Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generation/artifacts` | Generate artifact |
| GET | `/api/generation/artifacts/{artifact_id}` | Get artifact by ID |
| GET | `/api/generation/types` | List available artifact types |
| POST | `/api/generation/bulk` | Bulk generate artifacts |

## RAG System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rag/status` | RAG index status |
| POST | `/api/rag/search` | Search indexed documents |
| POST | `/api/rag/reindex` | Trigger reindexing |
| GET | `/api/rag/stats` | Index statistics |

## Knowledge Graph

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/knowledge-graph/status` | KG build status |
| GET | `/api/knowledge-graph/nodes` | Get graph nodes |
| GET | `/api/knowledge-graph/edges` | Get graph edges |
| POST | `/api/knowledge-graph/build` | Build/rebuild graph |
| GET | `/api/knowledge-graph/export` | Export graph data |

## Pattern Mining

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/pattern-mining/status` | Pattern mining status |
| GET | `/api/pattern-mining/patterns` | Get detected patterns |
| GET | `/api/pattern-mining/code-smells` | Get code smells |
| GET | `/api/pattern-mining/security-issues` | Get security issues |
| POST | `/api/pattern-mining/analyze` | Trigger analysis |

## Models

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | List all models |
| GET | `/api/models/{model_id}` | Get model details |
| POST | `/api/models/refresh` | Refresh model list |
| GET | `/api/models/routing` | Get model routing config |
| PUT | `/api/models/routing` | Update model routing |

## Training

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/training/jobs` | List training jobs |
| POST | `/api/training/jobs` | Start training job |
| GET | `/api/training/jobs/{job_id}` | Get job status |
| DELETE | `/api/training/jobs/{job_id}` | Cancel job |

## Feedback

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/feedback` | Submit feedback |
| GET | `/api/feedback/stats` | Feedback statistics |
| GET | `/api/feedback/examples` | Get feedback examples |

## Meeting Notes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/meeting-notes` | List meeting notes |
| POST | `/api/meeting-notes` | Create meeting note |
| GET | `/api/meeting-notes/{id}` | Get meeting note |
| PUT | `/api/meeting-notes/{id}` | Update meeting note |
| DELETE | `/api/meeting-notes/{id}` | Delete meeting note |

## Versions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/versions` | List all versions |
| GET | `/api/versions/{artifact_id}` | Get versions for artifact |
| GET | `/api/versions/{artifact_id}/diff` | Compare versions |

## Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/message` | Send chat message |
| GET | `/api/chat/history` | Get chat history |

## WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/generation` | Real-time generation updates |
| `/ws/training` | Training progress updates |

## Universal Context

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/universal-context` | Get universal context |
| POST | `/api/universal-context/build` | Build universal context |
| GET | `/api/universal-context/status` | Build status |

## Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/export/markdown` | Export as Markdown |
| POST | `/api/export/html` | Export as HTML |
| POST | `/api/export/json` | Export as JSON |

## Validation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/validation/validate` | Validate artifact |
| GET | `/api/validation/validators` | List validators |

## Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Get configuration |
| PUT | `/api/config` | Update configuration |
| GET | `/api/config/api-keys` | Get API key status |

---

## Authentication

Most endpoints accept optional authentication:
- **JWT Token:** `Authorization: Bearer <token>`
- **API Key:** `X-API-Key: <key>`

For development, authentication is optional (default user returned).

## Rate Limiting

- Login: 10 requests/minute
- Generation: 30 requests/minute
- Other endpoints: 100 requests/minute

## Error Response Format

```json
{
  "error": "ErrorType",
  "message": "Human-readable message",
  "type": "ExceptionClassName",
  "request_id": "uuid",
  "timestamp": "2025-11-24T12:00:00Z"
}
```

