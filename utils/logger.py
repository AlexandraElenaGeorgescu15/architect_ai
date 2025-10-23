"""
Production-Ready Logging System
Structured logging with JSON format for production monitoring
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class StructuredLogger:
    """Production-ready structured logger"""
    
    def __init__(self, name: str = "architect_ai", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # File handler (JSON format)
        log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        
        # Console handler (human-readable)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        ))
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _format_log(self, level: str, message: str, **kwargs) -> str:
        """Format log entry as JSON"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
            **kwargs
        }
        return json.dumps(log_entry)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(self._format_log("INFO", message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(self._format_log("WARNING", message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(self._format_log("ERROR", message, **kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(self._format_log("DEBUG", message, **kwargs))
    
    def generation_event(self, artifact_type: str, tokens: int, cost: float, success: bool):
        """Log generation event"""
        self.info(
            f"Generation: {artifact_type}",
            event_type="generation",
            artifact_type=artifact_type,
            tokens=tokens,
            cost=cost,
            success=success
        )
    
    def api_call(self, provider: str, model: str, tokens: int, latency_ms: float):
        """Log API call"""
        self.info(
            f"API Call: {provider}/{model}",
            event_type="api_call",
            provider=provider,
            model=model,
            tokens=tokens,
            latency_ms=latency_ms
        )
    
    def error_event(self, error_type: str, error_message: str, stack_trace: str = None):
        """Log error event"""
        self.error(
            f"Error: {error_type}",
            event_type="error",
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace
        )


def get_logger(name: str = "architect_ai") -> StructuredLogger:
    """Get or create logger instance"""
    return StructuredLogger(name)

