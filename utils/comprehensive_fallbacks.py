"""
Lightweight helper utilities for model capability detection.

Provides simple capability checks without complex error handling.
"""

import logging

logger = logging.getLogger(__name__)


def safe_parallel(provider_name: str, artifact_types: list, enable_parallel: bool):
    """
    Check if a provider supports parallel processing.
    
    Args:
        provider_name: Name of the AI provider
        artifact_types: List of artifact types to generate
        enable_parallel: Whether parallel processing is enabled
        
    Returns:
        Tuple of (can_parallel: bool, max_concurrent: int, reason: str)
    """
    # Simple capability detection
    parallel_capable_providers = {
        'Gemini': (True, 3, "Gemini supports parallel processing (max 3 concurrent)"),
        'OpenAI': (True, 2, "OpenAI supports parallel processing (max 2 concurrent)"),
        'Claude': (True, 2, "Claude supports parallel processing (max 2 concurrent)"),
        'Anthropic': (True, 2, "Anthropic supports parallel processing (max 2 concurrent)"),
    }
    
    # Normalize provider name (remove emojis, trim)
    clean_provider = provider_name.strip()
    for prefix in ["Local:", "Local", "Fine-Tuned"]:
        clean_provider = clean_provider.replace(prefix, "").strip()
    
    # Check if provider supports parallel
    if not enable_parallel:
        return False, 1, f"{provider_name}: Parallel processing disabled by user"
    
    # Check if provider is in the capable list
    for provider_key, (can_parallel, max_concurrent, reason) in parallel_capable_providers.items():
        if provider_key.lower() in clean_provider.lower():
            return can_parallel, max_concurrent, reason
    
    # Default: assume local/unknown models don't support parallel
    return False, 1, f"{provider_name}: Parallel processing not supported"


# Stub functions for backward compatibility (not used)
def safe_rag(agent, query, max_chunks=18, force_refresh=False):
    """DEPRECATED: Use agent.retrieve_rag_context() directly."""
    agent.retrieve_rag_context(query, force_refresh=force_refresh)
    return {'success': True}


def safe_ai(agent, method_name, *args, **kwargs):
    """DEPRECATED: Call agent methods directly."""
    method = getattr(agent, method_name)
    return method(*args, **kwargs)


def safe_file(operation, *args, **kwargs):
    """DEPRECATED: Call file operations directly."""
    return operation(*args, **kwargs)


def safe_diagram(code, diagram_type):
    """DEPRECATED: Use diagram processing directly."""
    return code


def safe_html(code, notes, diagram_type):
    """DEPRECATED: Use HTML generation directly."""
    return code
