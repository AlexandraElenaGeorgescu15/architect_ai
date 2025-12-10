"""
Intelligent tool self-detection for automatic exclusion from repo scans.

This module provides a single source of truth for detecting where the Architect.AI
tool is located, so all repo scanners can exclude it automatically without hardcoding.
"""

from pathlib import Path
from typing import Optional


def detect_tool_directory() -> Optional[Path]:
    """
    Detect the Architect.AI tool directory by looking for sentinel files.
    
    Returns:
        Path to the tool directory, or None if not found
    """
    # Start from this file's location (we know we're inside the tool)
    current = Path(__file__).resolve().parent.parent  # Go up to tool root
    
    # Verify this is the tool by checking for sentinel files
    sentinel_files = [
        "backend/main.py",
        "launch.py",
        "rag/ingest.py",
        "frontend/package.json"
    ]
    
    matches = sum(1 for sentinel in sentinel_files if (current / sentinel).exists())
    
    # If at least 2 sentinels found, this is the tool directory
    if matches >= 2:
        return current
    
    # Fallback: search up to 3 levels up
    check_path = current
    for _ in range(3):
        parent = check_path.parent
        if parent == check_path:
            break
        
        matches = sum(1 for sentinel in sentinel_files if (parent / sentinel).exists())
        if matches >= 2:
            return parent
        
        check_path = parent
    
    return None


def get_user_project_root() -> Path:
    """
    Get the user's project root (parent of tool directory).
    
    Returns:
        Path to user project root
    """
    tool_dir = detect_tool_directory()
    
    if tool_dir:
        # User project is the parent of the tool
        return tool_dir.parent
    
    # Fallback to current working directory
    return Path.cwd()


def should_exclude_path(path: Path) -> bool:
    """
    Check if a path should be excluded from repo scanning.
    
    Args:
        path: Path to check
        
    Returns:
        True if path should be excluded, False otherwise
    """
    # Common directories and files to exclude
    EXCLUDE_PATTERNS = {
        # Python
        '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache', 
        'site-packages', 'dist', 'build', '*.egg-info',
        # Node.js / JavaScript
        'node_modules', '.npm', '.yarn', 'bower_components',
        # .NET
        'bin', 'obj', 'packages', '.vs', '.vscode',
        # General
        '.git', '.svn', '.hg', '.idea', 
        'coverage', '.coverage', 'htmlcov',
        # Build outputs
        'out', 'target', 'tmp', 'temp',
    }
    
    # Check path components against exclusion patterns
    path_parts = set(path.parts)
    for part in path_parts:
        part_lower = part.lower()
        for pattern in EXCLUDE_PATTERNS:
            if pattern.startswith('*'):
                if part_lower.endswith(pattern[1:]):
                    return True
            elif part_lower == pattern or part_lower == pattern.lower():
                return True
    
    tool_dir = detect_tool_directory()
    
    if not tool_dir:
        return False
    
    try:
        # Check if path is inside tool directory
        path.relative_to(tool_dir)
        return True
    except ValueError:
        # Path is not relative to tool directory, don't exclude
        return False


def get_user_project_directories() -> list[Path]:
    """
    Get list of user project directories (siblings of tool directory).
    
    Returns:
        List of directories to scan
    """
    tool_dir = detect_tool_directory()
    
    if not tool_dir:
        # Fallback: return current directory
        return [Path.cwd()]
    
    parent = tool_dir.parent
    user_dirs = []
    
    for child in parent.iterdir():
        if (child.is_dir() and 
            child != tool_dir and 
            not child.name.startswith('.')):
            user_dirs.append(child)
    
    return user_dirs if user_dirs else [parent]

