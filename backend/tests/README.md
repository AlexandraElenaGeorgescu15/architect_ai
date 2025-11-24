# Backend Integration Tests

This directory contains integration tests for the FastAPI backend services.

## Test Structure

- `test_service_imports.py` - Tests that all services can be imported and initialized
- `test_integration.py` - Tests service interactions and workflows
- `test_api_endpoints.py` - Tests FastAPI endpoints with test client

## Running Tests

```bash
# Run all backend tests
pytest backend/tests/ -v

# Run specific test file
pytest backend/tests/test_service_imports.py -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=html
```

## Test Coverage

- Service initialization and imports
- Context Builder integration
- Generation -> Validation workflow
- Feedback collection
- RAG cache operations
- End-to-end workflows
- API endpoint structure

## Notes

- Some tests may require authentication (401 responses are expected)
- Some tests may require external services (Ollama, ChromaDB) - graceful degradation expected
- Integration tests are designed to verify service interactions, not full functionality



