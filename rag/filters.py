
from pathlib import Path
import re, fnmatch, hashlib, yaml

SECRET_RE = re.compile(r'(AKIA[0-9A-Z]{16}|SECRET|PASSWORD|TOKEN|API_KEY)', re.I)

# Prompt injection patterns to detect and neutralize
PROMPT_INJECTION_PATTERNS = [
    re.compile(r'\bignore\s+(previous|all|above)\s+instructions?\b', re.I),
    re.compile(r'\bforget\s+(everything|what|all)\b', re.I),
    re.compile(r'\bdo\s+not\s+follow\b', re.I),
    re.compile(r'\bdisregard\s+(previous|prior|all)\b', re.I),
    re.compile(r'\byou\s+are\s+now\b', re.I),  # "You are now DAN"
    re.compile(r'\bact\s+as\s+(if\s+)?you\s+(are|were)\b', re.I),
    re.compile(r'\brole\s*:\s*(system|assistant|user)\b', re.I),  # Role manipulation
    re.compile(r'<\s*/?\s*(system|user|assistant)\s*>', re.I),  # XML-style role tags
    re.compile(r'\[INST\]|\[/INST\]', re.I),  # Instruction markers
    re.compile(r'###\s*(Human|System|Assistant|User)\s*:', re.I),  # Markdown-style roles
]

# File extensions considered as code files
CODE_EXTS = (".ts", ".tsx", ".js", ".jsx", ".cs", ".py", ".sql")

def load_cfg():
    with open("rag/config.yaml","r",encoding="utf-8") as f:
        return yaml.safe_load(f)

def allow_file(path: Path, cfg) -> bool:
    if path.is_dir(): return False
    try:
        if path.stat().st_size > cfg["max_file_mb"]*1024*1024: return False
    except Exception:
        return False
    if not any(str(path).endswith(ext) for ext in cfg["allow_extensions"]): return False
    
    # Check ignore patterns using pathlib's match() which handles ** globbing
    path_str = str(path).replace('\\', '/')  # Normalize path separators
    for pat in cfg["ignore_globs"]:
        # Use Path.match() for proper ** glob support
        if path.match(pat) or fnmatch.fnmatch(path_str, pat):
            return False
    
    return True

def sanitize(text: str) -> str:
    return SECRET_RE.sub("***REDACTED***", text)

def sanitize_prompt_input(user_input: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent prompt injection attacks.
    
    This function:
    1. Truncates to max_length to prevent context window overflow
    2. Detects and neutralizes common prompt injection patterns
    3. Removes potentially dangerous control characters
    4. Logs any sanitization that was applied
    
    Args:
        user_input: Raw user input (query, context, etc.)
        max_length: Maximum allowed length (prevents context window overflow)
    
    Returns:
        Sanitized input safe for inclusion in prompts
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not user_input:
        return ""
    
    sanitized = user_input
    injection_detected = False
    
    # 1. Truncate to prevent context window overflow
    if len(sanitized) > max_length:
        logger.warning(f"⚠️ [PROMPT_SANITIZE] Input truncated from {len(sanitized)} to {max_length} chars")
        sanitized = sanitized[:max_length] + "\n[... truncated ...]"
    
    # 2. Detect and neutralize prompt injection patterns
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(sanitized):
            injection_detected = True
            # Replace with a neutralized version (add brackets to break the instruction)
            sanitized = pattern.sub(lambda m: f"[blocked: {m.group(0)}]", sanitized)
    
    if injection_detected:
        logger.warning(f"⚠️ [PROMPT_SANITIZE] Potential prompt injection detected and neutralized")
    
    # 3. Remove dangerous control characters (keep newlines and tabs)
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)
    
    return sanitized

def sha1(text:str)->str:
    return hashlib.sha1(text.encode("utf-8","ignore")).hexdigest()


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate token count for text to prevent context window overflow.
    
    This is a lightweight utility that can be called before building prompts
    to ensure we don't exceed LLM context limits.
    
    Args:
        text: Input text to count tokens for
        model: Model name for tokenizer selection (default: gpt-4)
    
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    try:
        # Try to use tiktoken for accurate counting
        import tiktoken
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback: rough estimate (4 chars per token on average)
        return len(text) // 4


def truncate_to_token_limit(text: str, max_tokens: int = 8000, model: str = "gpt-4") -> str:
    """
    Truncate text to fit within a token limit.
    
    Useful for ensuring context doesn't overflow the LLM's context window.
    
    Args:
        text: Input text to truncate
        max_tokens: Maximum token count allowed
        model: Model name for tokenizer selection
    
    Returns:
        Truncated text that fits within the token limit
    """
    if not text:
        return text
    
    current_tokens = estimate_tokens(text, model)
    
    if current_tokens <= max_tokens:
        return text
    
    # Binary search for the right length
    import logging
    logger = logging.getLogger(__name__)
    
    # Start with a conservative estimate based on ratio
    ratio = max_tokens / current_tokens
    truncated_len = int(len(text) * ratio * 0.95)  # 5% buffer
    
    truncated = text[:truncated_len]
    
    # Fine-tune by removing tokens until we fit
    while estimate_tokens(truncated, model) > max_tokens and len(truncated) > 100:
        truncated = truncated[:int(len(truncated) * 0.95)]
    
    logger.info(f"⚠️ [TOKEN_LIMIT] Text truncated from ~{current_tokens} to ~{estimate_tokens(truncated, model)} tokens")
    
    return truncated + "\n\n[... content truncated to fit context window ...]"
