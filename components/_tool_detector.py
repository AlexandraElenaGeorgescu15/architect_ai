"""
Intelligent tool self-detection for automatic exclusion from repo scans.

This module provides a single source of truth for detecting where the Architect.AI
tool is located, so all repo scanners can exclude it automatically without hardcoding.

ARCHITECTURE NOTE:
------------------
This is the ONLY place that should define what directories belong to the tool.
The ignore_globs in config.yaml should only contain UNIVERSAL patterns (node_modules, .git, etc.)
that apply to ANY project, not tool-specific folders.

This separation ensures:
1. User projects with folders like "components/", "services/", etc. are indexed correctly
2. The tool's own code is never indexed (self-contamination prevention)
3. Configuration is cleaner and more maintainable
"""

from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Sentinel files that identify the Architect.AI tool directory
TOOL_SENTINEL_FILES = [
    "backend/main.py",
    "launch.py", 
    "rag/ingest.py",
    "frontend/package.json",
    "components/_tool_detector.py",  # This file itself
]

# Directories that are part of the Architect.AI tool (relative to tool root)
# These will be excluded when scanning user projects
TOOL_DIRECTORIES = {
    "backend",
    "frontend", 
    "rag",
    "agents",
    "ai",
    "components",
    "archive",
    "data",
    "outputs",
    "context",
    "finetuned_models",
    "finetune_datasets",
    "training_jobs",
}


def detect_tool_directory() -> Optional[Path]:
    """
    Detect the Architect.AI tool directory by looking for sentinel files.
    
    Returns:
        Path to the tool directory, or None if not found
    """
    # Start from this file's location (we know we're inside the tool)
    current = Path(__file__).resolve().parent.parent  # Go up to tool root
    
    # Verify this is the tool by checking for sentinel files
    matches = sum(1 for sentinel in TOOL_SENTINEL_FILES if (current / sentinel).exists())
    
    # If at least 2 sentinels found, this is the tool directory
    if matches >= 2:
        logger.debug(f"Tool directory detected at: {current}")
        return current
    
    # Fallback: search up to 3 levels up
    check_path = current
    for _ in range(3):
        parent = check_path.parent
        if parent == check_path:
            break
        
        matches = sum(1 for sentinel in TOOL_SENTINEL_FILES if (parent / sentinel).exists())
        if matches >= 2:
            logger.debug(f"Tool directory detected at: {parent}")
            return parent
        
        check_path = parent
    
    logger.warning("Could not detect tool directory - self-exclusion may not work")
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
    
    This function handles TWO types of exclusions:
    1. Universal exclusions (node_modules, .git, etc.) - apply to ALL projects
    2. Tool self-exclusion - only excludes this tool's own code
    
    Args:
        path: Path to check
        
    Returns:
        True if path should be excluded, False otherwise
    """
    # Universal exclusions - these apply to ANY project
    UNIVERSAL_EXCLUDES = {
        # Python
        '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache', 
        'site-packages', '.egg-info',
        # Node.js / JavaScript
        'node_modules', '.npm', '.yarn', 'bower_components',
        # Build outputs (universal)
        'dist', 'build', 'out', 'target',
        # .NET build outputs
        'bin', 'obj', 'packages',
        # IDE/Editor
        '.vs', '.vscode', '.idea',
        # Version control
        '.git', '.svn', '.hg',
        # Test coverage
        'coverage', '.coverage', 'htmlcov',
        # Temp
        'tmp', 'temp',
    }
    
    # Check path components against universal exclusions
    path_parts = set(p.lower() for p in path.parts)
    for exclude in UNIVERSAL_EXCLUDES:
        if exclude.lower() in path_parts:
            return True
    
    # Tool self-exclusion: Check if path is inside the Architect.AI tool directory
    tool_dir = detect_tool_directory()
    
    if not tool_dir:
        return False
    
    try:
        # Check if path is inside tool directory
        path.resolve().relative_to(tool_dir.resolve())
        logger.debug(f"Excluding tool file: {path} (inside {tool_dir})")
        return True
    except ValueError:
        # Path is not relative to tool directory - this is USER code, don't exclude
        return False


def is_tool_path(path: Path) -> bool:
    """
    Check if a path is part of the Architect.AI tool (not a user project).
    
    This is useful for determining if we're analyzing our own code vs user code.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is part of the tool, False if it's user code
    """
    tool_dir = detect_tool_directory()
    if not tool_dir:
        return False
    
    try:
        path.resolve().relative_to(tool_dir.resolve())
        return True
    except ValueError:
        return False


def get_user_project_directories() -> list[Path]:
    """
    Get list of user project directories (siblings of tool directory).
    
    Automatically excludes:
    - The Architect.AI tool directory itself
    - Hidden directories (starting with .)
    - Common utility/internal folder names (agents, node_modules, etc.)
    
    Returns:
        List of directories to scan
    """
    # Folders that should never be returned as user projects
    EXCLUDED_FOLDER_NAMES = {
        'agents', 'components', 'utils', 'shared', 'common', 'lib', 'libs',
        'node_modules', '__pycache__', '.git', 'dist', 'build', 'bin', 'obj',
        'archive', 'backup', 'temp', 'tmp', 'cache', '.cache', 'logs',
    }
    
    tool_dir = detect_tool_directory()
    
    if not tool_dir:
        # Fallback: return current directory
        return [Path.cwd()]
    
    parent = tool_dir.parent
    user_dirs = []
    
    for child in parent.iterdir():
        if (child.is_dir() and 
            child != tool_dir and 
            not child.name.startswith('.') and
            child.name.lower() not in EXCLUDED_FOLDER_NAMES):
            user_dirs.append(child)
    
    return user_dirs if user_dirs else [parent]

