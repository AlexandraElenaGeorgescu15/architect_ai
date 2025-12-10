# Architect.AI - Code Conventions

## Python (Backend)

### Style
- Follow PEP 8 guidelines
- Use type hints on all function signatures
- Maximum line length: 100 characters
- Use `black` for formatting (optional)

### Imports
```python
# Standard library
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging

# Local
from backend.core.config import settings
from backend.services.generation_service import GenerationService
```

### Naming
- Classes: `PascalCase` (e.g., `GenerationService`)
- Functions/methods: `snake_case` (e.g., `generate_artifact`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- Private: prefix with `_` (e.g., `_internal_method`)

### Async/Await
- Use `async def` for I/O-bound operations
- Use `await` for async calls
- Avoid blocking calls in async functions

### Error Handling
```python
try:
    result = await service.generate(request)
except ValidationError as e:
    raise HTTPException(status_code=400, detail=str(e))
except ServiceError as e:
    logger.error(f"Service error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal error")
```

### Logging
```python
logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed debug info")
logger.info("Normal operation info")
logger.warning("Warning condition")
logger.error("Error occurred", exc_info=True)
```

### Pydantic Models
```python
class ArtifactRequest(BaseModel):
    """Request model for artifact generation."""
    artifact_type: str
    context_id: Optional[str] = None
    options: Dict[str, Any] = {}
    
    class Config:
        extra = "forbid"  # Reject unknown fields
```

## TypeScript (Frontend)

### Style
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use `const` over `let` when possible

### Naming
- Components: `PascalCase` (e.g., `ArtifactViewer`)
- Functions/hooks: `camelCase` (e.g., `useGeneration`)
- Types/interfaces: `PascalCase` (e.g., `ArtifactType`)
- Constants: `UPPER_SNAKE_CASE` or `camelCase`

### Component Structure
```typescript
import { useState, useEffect } from 'react';
import { useArtifactStore } from '../stores/artifactStore';

interface ArtifactViewerProps {
  artifactId: string;
  onClose?: () => void;
}

export function ArtifactViewer({ artifactId, onClose }: ArtifactViewerProps) {
  const [loading, setLoading] = useState(false);
  const { artifact, fetchArtifact } = useArtifactStore();

  useEffect(() => {
    fetchArtifact(artifactId);
  }, [artifactId]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="artifact-viewer">
      {/* Component content */}
    </div>
  );
}
```

### State Management (Zustand)
```typescript
import { create } from 'zustand';

interface ArtifactState {
  artifacts: Artifact[];
  loading: boolean;
  fetchArtifacts: () => Promise<void>;
}

export const useArtifactStore = create<ArtifactState>((set) => ({
  artifacts: [],
  loading: false,
  fetchArtifacts: async () => {
    set({ loading: true });
    const artifacts = await api.getArtifacts();
    set({ artifacts, loading: false });
  },
}));
```

### Tailwind CSS
- Use utility classes directly
- Extract common patterns to components
- Use dark mode variants: `dark:bg-gray-800`

## API Conventions

### Endpoints
- Use RESTful naming: `/api/artifacts`, `/api/models`
- Use plural nouns for collections
- Use HTTP methods correctly: GET, POST, PUT, DELETE

### Request/Response
- Use Pydantic models for validation
- Return consistent error format
- Include request ID in responses

### Status Codes
- 200: Success
- 201: Created
- 400: Bad Request (validation error)
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

## Git Conventions

### Commit Messages
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Branch Naming
- `feature/description`
- `fix/description`
- `refactor/description`

