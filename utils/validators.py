"""
Input Validation and Security
Validates user inputs and prevents common security issues
"""

import re
from typing import Tuple, List
from pathlib import Path

class InputValidator:
    """Validates user inputs for security and correctness"""
    
    # Security patterns to detect
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',                 # JavaScript injection
        r'on\w+\s*=',                  # Event handlers
        r'eval\s*\(',                  # Code execution
        r'exec\s*\(',                  # Code execution
        r'__import__',                 # Python imports
        r'subprocess',                 # System commands
        r'os\.system',                 # System commands
    ]
    
    MAX_INPUT_LENGTH = 50000  # 50KB max
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max
    
    @staticmethod
    def validate_text_input(text: str, field_name: str = "input") -> Tuple[bool, str]:
        """
        Validate text input for security issues.
        
        Returns:
            (is_valid, error_message)
        """
        if not text:
            return False, f"{field_name} cannot be empty"
        
        if len(text) > InputValidator.MAX_INPUT_LENGTH:
            return False, f"{field_name} exceeds maximum length ({InputValidator.MAX_INPUT_LENGTH} chars)"
        
        # Check for dangerous patterns
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, f"{field_name} contains potentially dangerous content"
        
        return True, ""
    
    @staticmethod
    def validate_file_upload(file_path: Path) -> Tuple[bool, str]:
        """
        Validate uploaded file.
        
        Returns:
            (is_valid, error_message)
        """
        if not file_path.exists():
            return False, "File does not exist"
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > InputValidator.MAX_FILE_SIZE:
            return False, f"File too large (max {InputValidator.MAX_FILE_SIZE / 1024 / 1024}MB)"
        
        # Check file extension
        allowed_extensions = {'.md', '.txt'}
        if file_path.suffix.lower() not in allowed_extensions:
            return False, f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        
        return True, ""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path separators and dangerous characters
        filename = re.sub(r'[/\\<>:"|?*]', '_', filename)
        # Remove leading dots
        filename = filename.lstrip('.')
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        return filename
    
    @staticmethod
    def validate_api_key(api_key: str, provider: str) -> Tuple[bool, str]:
        """
        Validate API key format.
        
        Returns:
            (is_valid, error_message)
        """
        if not api_key:
            return False, "API key cannot be empty"
        
        if len(api_key) < 20:
            return False, "API key too short"
        
        if len(api_key) > 500:
            return False, "API key too long"
        
        # Provider-specific validation
        if provider == "OpenAI" and not api_key.startswith("sk-"):
            return False, "Invalid OpenAI API key format (should start with 'sk-')"
        
        return True, ""
    
    @staticmethod
    def validate_diagram_content(content: str) -> Tuple[bool, str]:
        """
        Validate diagram content.
        
        Returns:
            (is_valid, error_message)
        """
        if not content:
            return False, "Diagram content cannot be empty"
        
        # Check for valid diagram types
        valid_types = ['graph', 'flowchart', 'sequenceDiagram', 'erDiagram', 'classDiagram']
        if not any(content.strip().startswith(dtype) for dtype in valid_types):
            return False, "Invalid diagram type"
        
        # Check length
        if len(content) > 10000:
            return False, "Diagram too large"
        
        return True, ""


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    def is_allowed(self) -> Tuple[bool, str]:
        """
        Check if request is allowed.
        
        Returns:
            (is_allowed, error_message)
        """
        import time
        now = time.time()
        
        # Remove old requests outside window
        self.requests = [req for req in self.requests if now - req < self.window_seconds]
        
        if len(self.requests) >= self.max_requests:
            return False, f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds}s"
        
        self.requests.append(now)
        return True, ""


def get_validator() -> InputValidator:
    """Get validator instance"""
    return InputValidator()


def get_rate_limiter(max_requests: int = 60) -> RateLimiter:
    """Get rate limiter instance"""
    return RateLimiter(max_requests=max_requests)

