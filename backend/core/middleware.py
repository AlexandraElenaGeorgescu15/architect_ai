"""
Custom middleware for FastAPI.
Includes rate limiting, request ID tracking, timing, trusted hosts, and IP banning.
"""

import time
import uuid
import logging
import re
from typing import Callable, Dict, Set, List
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# Rate limiter (in-memory, can be upgraded to Redis)
limiter = Limiter(key_func=get_remote_address)


# =============================================================================
# IP Ban Manager - Tracks repeated 404s and bans suspicious IPs
# =============================================================================
class IPBanManager:
    """
    Manages IP banning based on repeated 404 errors (vulnerability scanning detection).
    
    Strategy:
    - Track 404 counts per IP within a time window
    - Ban IPs that exceed threshold
    - Auto-expire bans after a configurable duration
    """
    
    def __init__(
        self,
        ban_threshold: int = 10,       # 404s before ban
        window_seconds: int = 60,       # Time window for counting 404s
        ban_duration_seconds: int = 300 # 5 minute ban
    ):
        self.ban_threshold = ban_threshold
        self.window_seconds = window_seconds
        self.ban_duration_seconds = ban_duration_seconds
        
        # Track 404 counts: ip -> list of timestamps
        self._404_counts: Dict[str, list] = defaultdict(list)
        # Banned IPs: ip -> ban expiry time
        self._banned_ips: Dict[str, datetime] = {}
        
        # Suspicious path patterns (vulnerability scanning indicators)
        self.suspicious_patterns = [
            "/cgi-bin/", "/.asp", "/.php", "/.env", 
            "/wp-admin", "/wp-content", "/phpmyadmin",
            "../", "..\\", "/etc/passwd", "/win.ini",
            ".git/", ".svn/", "/.htaccess", "/xmlrpc.php",
            "/admin/", "/administrator/", "/config/", "/backup/"
        ]
    
    def is_banned(self, ip: str) -> bool:
        """Check if an IP is currently banned."""
        if ip in self._banned_ips:
            if datetime.now() < self._banned_ips[ip]:
                return True
            else:
                # Ban expired, remove it
                del self._banned_ips[ip]
                logger.info(f"🔓 [IP_BAN] Ban expired for {ip}")
        return False
    
    def record_404(self, ip: str, path: str) -> bool:
        """
        Record a 404 error for an IP.
        
        Returns:
            True if IP should now be banned
        """
        now = datetime.now()
        
        # Check if path matches suspicious patterns (more severe)
        is_suspicious = any(pattern in path.lower() for pattern in self.suspicious_patterns)
        
        # Clean old entries outside the window
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._404_counts[ip] = [ts for ts in self._404_counts[ip] if ts > cutoff]
        
        # Add current 404
        # Suspicious paths count more heavily
        if is_suspicious:
            self._404_counts[ip].extend([now] * 3)  # Count as 3 404s
            logger.warning(f"🚨 [SECURITY] Suspicious path accessed: {path} from {ip}")
        else:
            self._404_counts[ip].append(now)
        
        # Check if threshold exceeded
        if len(self._404_counts[ip]) >= self.ban_threshold:
            self._banned_ips[ip] = now + timedelta(seconds=self.ban_duration_seconds)
            self._404_counts[ip] = []  # Clear counter
            logger.warning(f"🔒 [IP_BAN] Banned IP {ip} for {self.ban_duration_seconds}s (too many 404s)")
            return True
        
        return False
    
    def get_stats(self) -> Dict:
        """Get current ban statistics."""
        return {
            "banned_ips_count": len(self._banned_ips),
            "tracked_ips_count": len(self._404_counts),
            "banned_ips": list(self._banned_ips.keys())
        }


# Global IP ban manager
ip_ban_manager = IPBanManager()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to all requests for tracing."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID header and log request."""
        # Only process HTTP requests
        if request.scope.get("type") != "http":
            return await call_next(request)

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
        # Only process HTTP requests
        if request.scope.get("type") != "http":
            return await call_next(request)

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


class IPBanMiddleware(BaseHTTPMiddleware):
    """
    Middleware to block banned IPs from accessing the API.
    
    Works with IPBanManager to detect and block vulnerability scanners.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check if IP is banned before processing request."""
        # Only process HTTP requests
        if request.scope.get("type") != "http":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        
        # Check if IP is banned
        if ip_ban_manager.is_banned(client_ip):
            logger.warning(f"🚫 [IP_BAN] Blocked request from banned IP: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "message": "Your IP has been temporarily blocked due to suspicious activity.",
                    "type": "ip_banned"
                }
            )
        
        # Process the request
        response = await call_next(request)
        
        # Track 404s for potential banning
        if response.status_code == 404:
            path = request.url.path
            if ip_ban_manager.record_404(client_ip, path):
                # IP just got banned, but let this request complete
                logger.warning(f"🔒 [IP_BAN] IP {client_ip} banned after excessive 404s")
        
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
        # Only process HTTP requests
        if request.scope.get("type") != "http":
            return await call_next(request)

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
        # CRITICAL: Always log generation requests for debugging
        is_generation_request = path.startswith("/api/generation/")
        if not skip_logging or is_generation_request:
            log_level = "info" if not is_generation_request else "warning"  # Make generation requests more visible
            logger.log(
                logging.WARNING if is_generation_request else logging.INFO,
                f"🌐 [MIDDLEWARE] {'=' * 20} REQUEST RECEIVED {'=' * 20}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "query": str(request.query_params),
                    "client": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "is_generation": is_generation_request,
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


class CustomTrustedHostMiddleware(BaseHTTPMiddleware):
    """
    Custom TrustedHostMiddleware that properly handles ngrok wildcards.
    
    This replaces Starlette's TrustedHostMiddleware which doesn't support wildcard patterns.
    """
    
    def __init__(self, app, allowed_hosts: List[str]):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts
        # Compile ngrok patterns for faster matching
        ngrok_patterns = [
            r".*\.ngrok(-free)?\.(app|io|dev|com)$",
            r".*\.ngrok\.(app|io)$",
        ]
        self.ngrok_regexes = [re.compile(pattern) for pattern in ngrok_patterns]
    
    def is_host_allowed(self, host: str) -> bool:
        """Check if host is in allowed list or matches ngrok patterns."""
        if not host:
            return False
        
        # Remove port if present
        host_without_port = host.split(':')[0]
        
        # Check exact matches
        if host_without_port in self.allowed_hosts or host in self.allowed_hosts:
            return True
        
        # Check ngrok patterns
        return any(regex.match(host_without_port) for regex in self.ngrok_regexes)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate Host header before processing request."""
        # Only process HTTP requests
        if request.scope.get("type") != "http":
            return await call_next(request)
        
        # Get host from request
        host = request.headers.get("host", "")
        
        # Validate host (includes ngrok pattern checking)
        if not self.is_host_allowed(host):
            logger.warning(f"🚫 [TRUSTED_HOST] Rejected request from untrusted host: {host}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "message": f"Host '{host}' is not allowed. Please use a trusted host.",
                    "type": "invalid_host"
                }
            )
        
        return await call_next(request)


def setup_security_middleware(app, allowed_hosts: list = None):
    """
    Setup comprehensive security middleware for FastAPI app.
    
    This includes:
    - NgrokHostMiddleware: Allow ngrok domains (runs first)
    - CustomTrustedHostMiddleware: Only accept requests from allowed hosts (replaces TrustedHostMiddleware)
    - IPBanMiddleware: Block IPs with suspicious behavior (repeated 404s)
    
    Args:
        app: FastAPI application instance
        allowed_hosts: List of allowed hostnames (default: localhost + ngrok patterns)
    """
    from backend.core.config import settings
    
    # Default allowed hosts: localhost, 127.0.0.1, and ngrok tunnels
    if allowed_hosts is None:
        allowed_hosts = [
            "localhost",
            "127.0.0.1",
            "::1",
            "[::1]",
            "0.0.0.0",
            # Frontend origins (extracted from CORS settings)
            "localhost:3000",
            "127.0.0.1:3000",
        ]
        
        # Add configured CORS origins
        if hasattr(settings, 'cors_origins'):
            for origin in settings.cors_origins:
                # Extract host from URL
                if origin.startswith("http://") or origin.startswith("https://"):
                    from urllib.parse import urlparse
                    parsed = urlparse(origin)
                    if parsed.netloc:
                        allowed_hosts.append(parsed.netloc)
                else:
                    allowed_hosts.append(origin)
    
    # Add CustomTrustedHostMiddleware (validates Host header, supports ngrok wildcards)
    # This replaces Starlette's TrustedHostMiddleware which doesn't support wildcard patterns
    # Note: This must be added after CORS middleware in main.py (CORS is added last, so executes first)
    app.add_middleware(
        CustomTrustedHostMiddleware,
        allowed_hosts=allowed_hosts
    )
    
    # Add IP Ban Middleware (blocks banned IPs)
    app.add_middleware(IPBanMiddleware)
    
    logger.info(f"[SECURITY] Security middleware configured with {len(allowed_hosts)} allowed hosts")
    logger.info(f"[SECURITY] IP ban threshold: {ip_ban_manager.ban_threshold} 404s in {ip_ban_manager.window_seconds}s")
    
    return ip_ban_manager


def get_ip_ban_stats() -> Dict:
    """Get current IP ban statistics."""
    return ip_ban_manager.get_stats()

