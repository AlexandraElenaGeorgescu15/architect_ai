"""
Enhanced structured logging with context propagation.
Provides contextual logging with request IDs, user info, and performance data.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime
from contextvars import ContextVar

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings

# Context variables for request-scoped data
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
operation_var: ContextVar[Optional[str]] = ContextVar('operation', default=None)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add context variables
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id
        
        operation = operation_var.get()
        if operation:
            log_data["operation"] = operation
        
        # Add extra fields from record
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add stack trace for errors
        if record.levelno >= logging.ERROR:
            import traceback
            log_data["stack_trace"] = traceback.format_stack()
        
        return json.dumps(log_data, default=str)


class ContextLogger:
    """
    Enhanced logger with context propagation.
    """
    
    def __init__(self, name: str):
        """Initialize context logger."""
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _log_with_context(
        self,
        level: int,
        message: str,
        *args,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log with context variables."""
        context_extra = {}
        
        request_id = request_id_var.get()
        if request_id:
            context_extra["request_id"] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            context_extra["user_id"] = user_id
        
        operation = operation_var.get()
        if operation:
            context_extra["operation"] = operation
        
        if extra:
            context_extra.update(extra)
        
        self.logger.log(level, message, *args, extra=context_extra if context_extra else None, **kwargs)
    
    def debug(self, message: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, *args, extra=extra, **kwargs)
    
    def info(self, message: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, *args, extra=extra, **kwargs)
    
    def warning(self, message: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, *args, extra=extra, **kwargs)
    
    def error(self, message: str, *args, extra: Optional[Dict[str, Any]] = None, exc_info=None, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, *args, extra=extra, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, *args, extra: Optional[Dict[str, Any]] = None, exc_info=None, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, *args, extra=extra, exc_info=exc_info, **kwargs)
    
    def log_performance(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log performance metrics.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
            success: Whether operation succeeded
            metadata: Additional metadata
        """
        extra = {
            "operation": operation,
            "duration": duration,
            "success": success,
            "performance": True
        }
        if metadata:
            extra.update(metadata)
        
        level = logging.INFO if success else logging.WARNING
        self._log_with_context(
            level,
            f"Performance: {operation} took {duration:.3f}s",
            extra=extra
        )


def get_logger(name: str) -> ContextLogger:
    """
    Get a context-aware logger.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        ContextLogger instance
    """
    return ContextLogger(name)


def setup_logging():
    """
    Setup structured logging configuration.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler with structured formatter
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Use structured formatter if JSON logging is enabled
    if settings.debug or getattr(settings, 'json_logging', False):
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(settings.log_format)
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # UTF-8 console wrapper for Windows compatibility
    if sys.platform == 'win32':
        try:
            import io
            if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except (AttributeError, OSError, ValueError):
            pass
    
    logging.info("Structured logging configured")


# Initialize logging on import
setup_logging()

