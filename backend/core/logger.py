"""
Enhanced structured logging with exception tracking, AI token usage, and JSONL file output.

Features:
- Captures all exceptions with full context
- Tracks AI token usage and costs
- Writes to logs/errors.jsonl with timestamps
- Context propagation for request tracing
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from functools import wraps
import logging
import json
from datetime import datetime
from contextvars import ContextVar
import traceback
import threading

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings

# Context variables for request-scoped data
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
operation_var: ContextVar[Optional[str]] = ContextVar('operation', default=None)

# Ensure logs directory exists
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# File paths for JSONL outputs
ERRORS_JSONL = LOGS_DIR / "errors.jsonl"
TOKENS_JSONL = LOGS_DIR / "tokens.jsonl"
AI_CALLS_JSONL = LOGS_DIR / "ai_calls.jsonl"

# Thread lock for file writes
_file_lock = threading.Lock()


# =============================================================================
# Cost Tracking for AI Models
# =============================================================================

# Cost per 1K tokens (USD) - Updated Jan 2026
MODEL_COSTS = {
    # OpenAI
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    
    # Anthropic Claude
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    
    # Google Gemini
    "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},  # Free tier
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    
    # Groq (free/cheap)
    "llama-3.3-70b-versatile": {"input": 0.0, "output": 0.0},
    "llama-3.1-70b-versatile": {"input": 0.0, "output": 0.0},
    "mixtral-8x7b-32768": {"input": 0.0, "output": 0.0},
    
    # Ollama (local - free)
    "llama3": {"input": 0.0, "output": 0.0},
    "llama3:8b": {"input": 0.0, "output": 0.0},
    "codellama": {"input": 0.0, "output": 0.0},
    "mistral": {"input": 0.0, "output": 0.0},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for AI model usage."""
    # Normalize model name
    model_lower = model.lower()
    
    # Find matching cost entry
    for model_key, costs in MODEL_COSTS.items():
        if model_key.lower() in model_lower or model_lower in model_key.lower():
            input_cost = (input_tokens / 1000) * costs["input"]
            output_cost = (output_tokens / 1000) * costs["output"]
            return input_cost + output_cost
    
    # Default: assume free/local
    return 0.0


# =============================================================================
# JSONL File Writers
# =============================================================================

def _write_jsonl(filepath: Path, data: Dict[str, Any]):
    """Thread-safe write to JSONL file."""
    with _file_lock:
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, default=str) + "\n")
        except Exception as e:
            # Last resort: print to stderr
            print(f"Failed to write to {filepath}: {e}", file=sys.stderr)


def log_error_to_file(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    module: Optional[str] = None,
    function: Optional[str] = None
):
    """
    Log an exception to logs/errors.jsonl.
    
    Args:
        error: The exception that occurred
        context: Additional context (request data, parameters, etc.)
        module: Module name where error occurred
        function: Function name where error occurred
    """
    error_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "exception",
        "error_class": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "module": module,
        "function": function,
        "request_id": request_id_var.get(),
        "user_id": user_id_var.get(),
        "operation": operation_var.get(),
        "context": context or {}
    }
    
    _write_jsonl(ERRORS_JSONL, error_data)


def log_token_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    operation: Optional[str] = None,
    artifact_type: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log AI token usage and cost to logs/tokens.jsonl.
    
    Args:
        model: Model name (e.g., "gpt-4", "llama3", "gemini-2.0-flash-exp")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        operation: Operation type (e.g., "generation", "chat", "validation")
        artifact_type: Artifact type if applicable
        duration_seconds: Time taken for the API call
        success: Whether the call succeeded
        metadata: Additional metadata
    """
    cost = calculate_cost(model, input_tokens, output_tokens)
    
    token_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "token_usage",
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": cost,
        "operation": operation or operation_var.get(),
        "artifact_type": artifact_type,
        "duration_seconds": duration_seconds,
        "success": success,
        "request_id": request_id_var.get(),
        "user_id": user_id_var.get(),
        "metadata": metadata or {}
    }
    
    _write_jsonl(TOKENS_JSONL, token_data)
    
    # Also log to standard logger for real-time visibility
    logger = logging.getLogger("ai.tokens")
    logger.info(
        f"🔢 Token usage: {model} | {input_tokens}→{output_tokens} tokens | ${cost:.6f}"
    )


def log_ai_call(
    model: str,
    prompt_length: int,
    response_length: int,
    operation: str,
    success: bool,
    duration_seconds: float,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log an AI API call to logs/ai_calls.jsonl.
    
    Args:
        model: Model name
        prompt_length: Length of the prompt in characters
        response_length: Length of the response in characters
        operation: Operation type
        success: Whether the call succeeded
        duration_seconds: Time taken
        error: Error message if failed
        metadata: Additional metadata
    """
    call_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "ai_call",
        "model": model,
        "prompt_length": prompt_length,
        "response_length": response_length,
        "operation": operation,
        "success": success,
        "duration_seconds": duration_seconds,
        "error": error,
        "request_id": request_id_var.get(),
        "user_id": user_id_var.get(),
        "metadata": metadata or {}
    }
    
    _write_jsonl(AI_CALLS_JSONL, call_data)


# =============================================================================
# Exception Capture Decorator
# =============================================================================

def capture_exceptions(
    reraise: bool = True,
    log_context: Optional[Callable[..., Dict[str, Any]]] = None
):
    """
    Decorator to capture and log all exceptions.
    
    Args:
        reraise: Whether to reraise the exception after logging
        log_context: Optional function to generate context dict from args/kwargs
    
    Usage:
        @capture_exceptions()
        async def my_function(arg1, arg2):
            ...
        
        @capture_exceptions(reraise=False, log_context=lambda x: {"input": x})
        def another_function(x):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = log_context(*args, **kwargs) if log_context else {}
                context["args"] = str(args)[:500]  # Truncate for safety
                context["kwargs"] = str(kwargs)[:500]
                
                log_error_to_file(
                    error=e,
                    context=context,
                    module=func.__module__,
                    function=func.__name__
                )
                
                if reraise:
                    raise
                return None
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = log_context(*args, **kwargs) if log_context else {}
                context["args"] = str(args)[:500]
                context["kwargs"] = str(kwargs)[:500]
                
                log_error_to_file(
                    error=e,
                    context=context,
                    module=func.__module__,
                    function=func.__name__
                )
                
                if reraise:
                    raise
                return None
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# =============================================================================
# Structured Formatter
# =============================================================================

class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
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
            # Also write to errors.jsonl
            try:
                exc_type, exc_value, exc_tb = record.exc_info
                if exc_value:
                    log_error_to_file(
                        error=exc_value,
                        context={"log_message": record.getMessage()},
                        module=record.module,
                        function=record.funcName
                    )
            except Exception:
                pass  # Don't fail logging because of error logging
        
        return json.dumps(log_data, default=str)


# =============================================================================
# Context Logger
# =============================================================================

class ContextLogger:
    """Enhanced logger with context propagation and exception tracking."""
    
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
        exc_info=None,
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
        
        self.logger.log(
            level, message, *args, 
            extra=context_extra if context_extra else None,
            exc_info=exc_info,
            **kwargs
        )
    
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
    
    def exception(self, message: str, *args, exc: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Log exception with full context and write to errors.jsonl.
        
        Args:
            message: Error message
            exc: The exception object (if not using exc_info=True)
            context: Additional context data
        """
        self._log_with_context(logging.ERROR, message, *args, exc_info=True, **kwargs)
        
        # Also write to JSONL
        if exc:
            log_error_to_file(
                error=exc,
                context=context or {},
                module=self.name,
                function=None
            )
    
    def log_performance(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log performance metrics."""
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
    
    def log_ai_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str = "generation",
        artifact_type: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log AI token usage and cost.
        
        Convenience method that also writes to tokens.jsonl.
        """
        log_token_usage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            operation=operation,
            artifact_type=artifact_type,
            duration_seconds=duration_seconds,
            success=success,
            metadata=metadata
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
    """Setup structured logging configuration."""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Use structured formatter if JSON logging is enabled
    if settings.json_logging:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(settings.log_format)
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Also create a file handler for errors (always structured)
    error_file_handler = logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8")
    error_file_handler.setLevel(logging.WARNING)
    error_file_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(error_file_handler)
    
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
    
    logging.info("Structured logging configured with JSONL outputs")


# =============================================================================
# Token Usage Summary
# =============================================================================

def get_token_usage_summary() -> Dict[str, Any]:
    """
    Get summary of token usage from logs/tokens.jsonl.
    
    Returns:
        Dictionary with usage statistics by model
    """
    if not TOKENS_JSONL.exists():
        return {"total_tokens": 0, "total_cost_usd": 0, "by_model": {}}
    
    total_tokens = 0
    total_cost = 0.0
    by_model: Dict[str, Dict[str, Any]] = {}
    
    try:
        with open(TOKENS_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("type") == "token_usage":
                        model = entry.get("model", "unknown")
                        tokens = entry.get("total_tokens", 0)
                        cost = entry.get("cost_usd", 0)
                        
                        total_tokens += tokens
                        total_cost += cost
                        
                        if model not in by_model:
                            by_model[model] = {"tokens": 0, "cost_usd": 0, "calls": 0}
                        
                        by_model[model]["tokens"] += tokens
                        by_model[model]["cost_usd"] += cost
                        by_model[model]["calls"] += 1
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    
    return {
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "by_model": by_model
    }


def get_error_summary() -> Dict[str, Any]:
    """
    Get summary of errors from logs/errors.jsonl.
    
    Returns:
        Dictionary with error statistics
    """
    if not ERRORS_JSONL.exists():
        return {"total_errors": 0, "by_type": {}, "recent": []}
    
    total_errors = 0
    by_type: Dict[str, int] = {}
    recent = []
    
    try:
        with open(ERRORS_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("type") == "exception":
                        total_errors += 1
                        error_class = entry.get("error_class", "Unknown")
                        by_type[error_class] = by_type.get(error_class, 0) + 1
                        
                        # Keep last 10 errors
                        recent.append({
                            "timestamp": entry.get("timestamp"),
                            "error_class": error_class,
                            "message": entry.get("error_message", "")[:200],
                            "module": entry.get("module"),
                            "function": entry.get("function")
                        })
                        if len(recent) > 10:
                            recent.pop(0)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    
    return {
        "total_errors": total_errors,
        "by_type": by_type,
        "recent": recent[-10:]  # Last 10
    }


# Initialize logging on import
setup_logging()
