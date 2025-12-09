"""
Custom middleware for FastAPI.
Includes rate limiting, request ID tracking, and timing.
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# Rate limiter (in-memory, can be upgraded to Redis)
limiter = Limiter(key_func=get_remote_address)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to all requests for tracing."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID header and log request."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Track request processing time with metrics."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add timing information to response headers and record metrics."""
        from backend.core.metrics import get_metrics_collector
        from backend.core.config import settings
        
        start_time = time.time()
        metrics = get_metrics_collector() if settings.metrics_enabled else None
        
        # Initialize response to default error response in case of failure
        response = Response("Internal Server Error", status_code=500)
        
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error and re-raise
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} after {process_time:.2f}s",
                extra={
                    "duration": process_time,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e)
                }
            )
            raise
        finally:
            # Always add timing header and metrics, even on error
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            
            # Record metrics
            if metrics:
                metrics.record(
                    "http_request_duration",
                    process_time,
                    tags={
                        "method": request.method,
                        "path": request.url.path,
                        "status": str(response.status_code)
                    }
                )
                metrics.increment(
                    "http_requests_total",
                    tags={
                        "method": request.method,
                        "path": request.url.path,
                        "status": str(response.status_code)
                    }
                )
            
            # Log slow requests
            if process_time > 1.0:
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {process_time:.2f}s",
                    extra={
                        "duration": process_time,
                        "method": request.method,
                        "path": request.url.path
                    }
                )
        
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Add structured logging for requests with context propagation."""
    
    # Paths to skip logging (health checks, metrics, static assets)
    SKIP_LOGGING_PATHS = {
        "/health",
        "/api/health",
        "/metrics",
        "/favicon.ico",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response with structured data and context."""
        from backend.core.logger import request_id_var, user_id_var, operation_var
        
        request_id = getattr(request.state, "request_id", "unknown")
        path = request.url.path
        
        # Skip logging for health checks and other noisy endpoints
        skip_logging = path in self.SKIP_LOGGING_PATHS or path.startswith("/api/health")
        
        # Set context variables
        request_id_var.set(request_id)
        
        # Try to get user ID from request state (if authenticated)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            user_id_var.set(str(user_id))
        
        # Set operation from path
        operation = f"{request.method} {path}"
        operation_var.set(operation)
        
        # Log request (skip for health checks)
        if not skip_logging:
            logger.info(
                "Request started",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "query": str(request.query_params),
                    "client": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                }
            )
        
        try:
            response = await call_next(request)
            
            # Log response (skip for health checks, unless there's an error)
            if not skip_logging or response.status_code >= 400:
                logger.info(
                    "Request completed",
                    extra={
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "method": request.method,
                        "path": path,
                    }
                )
            
            return response
            
        except Exception as e:
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise
        finally:
            # Clear context variables
            request_id_var.set(None)
            user_id_var.set(None)
            operation_var.set(None)


def setup_rate_limiting(app):
    """
    Setup rate limiting for FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return limiter



