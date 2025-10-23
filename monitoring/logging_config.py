"""
Logging Configuration and Observability
Structured logging with multiple outputs
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import sys

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

def setup_logging(
    level: str = "INFO",
    log_file: str = None,
    json_format: bool = False
) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        json_format: Use JSON formatting
    
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger('architect_ai')
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_format = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
    
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_format = logging.Formatter(
                '[%(asctime)s] %(levelname)s - %(name)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_format)
        
        logger.addHandler(file_handler)
    
    return logger

class LogContext:
    """Context manager for adding context to logs"""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.extra = self.context
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)

# Global logger instance
_logger = None

def get_logger(name: str = None) -> logging.Logger:
    """Get or create logger"""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    
    if name:
        return _logger.getChild(name)
    return _logger

