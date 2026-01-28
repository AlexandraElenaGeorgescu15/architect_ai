"""
Target Project Helper - Centralized helper for determining the user's target project.

This module provides a SINGLE SOURCE OF TRUTH for what project the user is analyzing.
All services (RAG, Knowledge Graph, Pattern Mining, Chat) should use this module
to get the target project path.

IMPORTANT: The target project is the USER'S project being analyzed,
NOT the Architect.AI tool itself.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


def get_target_project_path() -> Optional[Path]:
    """
    Get the target project path that the user is analyzing.
    
    Priority:
    1. Explicitly configured TARGET_REPO_PATH in settings/.env
    2. Auto-detected user project directories (siblings of tool)
    3. Parent of tool directory (mother project folder)
    
    Returns:
        Path to the target project, or None if not determinable
    """
    from backend.core.config import settings
    
    # Priority 1: Explicitly configured target
    if settings.target_repo_path:
        target = Path(settings.target_repo_path).resolve()
        if target.exists():
            logger.info(f"✅ [TARGET_PROJECT] Using configured path: {target}")
            return target
        else:
            logger.warning(f"⚠️ [TARGET_PROJECT] Configured path does not exist: {target}")
    
    # Priority 2: Auto-detect user project directories
    available = get_available_projects()
    
    if available:
        # Sort by score descending and pick the best (already sorted in get_available_projects)
        best_dir = available[0]
        logger.info(f"✅ [TARGET_PROJECT] Auto-detected project: {best_dir} (score: {score_directory(best_dir)})")
        return best_dir
    
    # Priority 3: Fallback to parent of tool (mother project folder)
    from backend.utils.tool_detector import detect_tool_directory
    tool_dir = detect_tool_directory()
    if tool_dir:
        parent = tool_dir.parent
        logger.warning(f"⚠️ [TARGET_PROJECT] Falling back to tool parent: {parent}")
        return parent
    
    logger.error("❌ [TARGET_PROJECT] Could not determine target project")
    return None


def get_available_projects() -> List[Path]:
    """
    Get all available user project directories.
    
    Returns:
        Sorted list of project paths (best projects first)
    """
    from backend.utils.tool_detector import get_user_project_directories, detect_tool_directory
    
    user_dirs = get_user_project_directories()
    tool_dir = detect_tool_directory()
    
    scored_dirs = []
    for d in user_dirs:
        # Resolve path for consistent comparison
        d_resolved = d.resolve()
        
        # Skip tool directory and non-existent folders
        if tool_dir and d_resolved == tool_dir.resolve():
            continue
        if not d_resolved.exists():
            continue
            
        score = score_directory(d_resolved)
        # Only include dirs that actually look like projects or are clearly NOT utility folders
        if score > -50:
            scored_dirs.append((d_resolved, score))
        else:
            logger.debug(f"⏭️ [TARGET_PROJECT] Skipping utility directory: {d_resolved.name} (score: {score})")
    
    # Sort by score descending
    scored_dirs.sort(key=lambda x: x[1], reverse=True)
    
    return [d for d, s in scored_dirs]


def get_target_project_name() -> str:
    """
    Get the name of the target project.
    
    Returns:
        Project name (directory name) or "Unknown Project"
    """
    target = get_target_project_path()
    if target:
        return target.name
    return "Unknown Project"


def get_target_project_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the target project.
    
    Returns:
        Dict with project info (name, path, tech_stack, markers, etc.)
    """
    target = get_target_project_path()
    if not target:
        return {
            "name": "Unknown Project",
            "path": None,
            "exists": False,
            "tech_stack": [],
            "markers": [],
            "file_count": 0
        }
    
    return {
        "name": target.name,
        "path": str(target),
        "exists": target.exists(),
        "tech_stack": detect_tech_stack(target),
        "markers": detect_project_markers(target),
        "file_count": count_source_files(target)
    }


def score_directory(directory: Path) -> int:
    """
    Score a directory to determine if it's a main project.
    Higher scores indicate more likely to be a real project.
    """
    score = 0
    name_lower = directory.name.lower()
    
    # Negative score for utility directories
    # Ported from backend/api/project_target.py EXCLUDED_FOLDER_NAMES
    EXCLUDED_FOLDER_NAMES = {
        'agents', 'components', 'utils', 'shared', 'common', 'lib', 'libs', 'tools',
        'node_modules', '__pycache__', '.git', 'dist', 'build', 'bin', 'obj',
        'archive', 'backup', 'temp', 'tmp', 'cache', '.cache', 'logs', 'venv', '.venv',
        'documentation', 'docs', 'reports'
    }
    
    if name_lower in EXCLUDED_FOLDER_NAMES:
        score -= 200 # Heavily penalize
    
    # Positive scores for project markers
    if (directory / 'package.json').exists():
        score += 50
    if (directory / 'angular.json').exists():
        score += 60
    if (directory / 'pom.xml').exists() or (directory / 'build.gradle').exists() or (directory / 'build.gradle.kts').exists():
        score += 50
    if (directory / 'Cargo.toml').exists():
        score += 50
    if (directory / 'go.mod').exists():
        score += 50
    if (directory / 'requirements.txt').exists() or (directory / 'setup.py').exists() or (directory / 'pyproject.toml').exists():
        score += 40
        
    # .NET detection - root and nested
    has_csproj = any(directory.glob('*.csproj')) or any(directory.glob('*/*.csproj'))
    has_sln = any(directory.glob('*.sln')) or any(directory.glob('*/*.sln'))
    
    if has_csproj:
        score += 50
    if has_sln:
        score += 55
        
    if (directory / 'src').is_dir():
        score += 30
    if (directory / 'frontend').is_dir():
        score += 20
    if (directory / 'backend').is_dir():
        score += 20
    
    # Bonus for project-like names
    if 'project' in name_lower or 'final' in name_lower or 'app' in name_lower:
        score += 25
    
    return score


def detect_tech_stack(project_path: Path) -> List[str]:
    """Detect the technology stack of a project."""
    if not project_path or not project_path.exists():
        return []
    
    tech_stack = []
    
    # Python
    if (project_path / "requirements.txt").exists() or \
       (project_path / "setup.py").exists() or \
       (project_path / "pyproject.toml").exists():
        tech_stack.append("Python")
    
    # JavaScript/TypeScript/Node.js
    if (project_path / "package.json").exists():
        tech_stack.append("Node.js")
        # Check for specific frameworks
        if (project_path / "angular.json").exists():
            tech_stack.append("Angular")
        elif (project_path / "next.config.js").exists() or (project_path / "next.config.mjs").exists():
            tech_stack.append("Next.js")
        elif any(project_path.rglob("*.tsx")):
            tech_stack.append("React")
    
    # TypeScript
    if (project_path / "tsconfig.json").exists():
        tech_stack.append("TypeScript")
    
    # Java
    if (project_path / "pom.xml").exists():
        tech_stack.append("Maven/Java")
    elif (project_path / "build.gradle").exists() or (project_path / "build.gradle.kts").exists():
        tech_stack.append("Gradle/Java")
    
    # .NET
    if any(project_path.glob("*.csproj")) or any(project_path.glob("*.sln")) or \
       any(project_path.glob("*/*.csproj")) or any(project_path.glob("*/*.sln")):
        tech_stack.append(".NET/C#")
    
    # Go
    if (project_path / "go.mod").exists():
        tech_stack.append("Go")
    
    # Rust
    if (project_path / "Cargo.toml").exists():
        tech_stack.append("Rust")
    
    # Docker
    if (project_path / "Dockerfile").exists() or (project_path / "docker-compose.yml").exists():
        tech_stack.append("Docker")
    
    return tech_stack


def detect_project_markers(directory: Path) -> List[str]:
    """Detect project type markers in a directory."""
    if not directory or not directory.exists():
        return []
    
    markers = []
    
    if (directory / 'package.json').exists():
        markers.append('Node.js')
    if (directory / 'angular.json').exists():
        markers.append('Angular')
    if (directory / 'pom.xml').exists():
        markers.append('Maven')
    if (directory / 'build.gradle').exists() or (directory / 'build.gradle.kts').exists():
        markers.append('Gradle')
    if (directory / 'requirements.txt').exists() or (directory / 'pyproject.toml').exists():
        markers.append('Python')
    if (directory / 'Cargo.toml').exists():
        markers.append('Rust')
    if (directory / 'go.mod').exists():
        markers.append('Go')
    
    # .NET detection
    if any(directory.glob('*.csproj')) or any(directory.glob('*/*.csproj')):
        markers.append('.NET')
    if any(directory.glob('*.sln')) or any(directory.glob('*/*.sln')):
        markers.append('.NET Solution')
    if (directory / 'src').is_dir():
        markers.append('Has src/')
    if (directory / 'frontend').is_dir():
        markers.append('Has frontend/')
    if (directory / 'backend').is_dir():
        markers.append('Has backend/')
    if (directory / '.git').is_dir():
        markers.append('Git repository')
    
    return markers


def count_source_files(project_path: Path) -> int:
    """Count the number of source files in a project."""
    if not project_path or not project_path.exists():
        return 0
    
    count = 0
    source_extensions = ['*.py', '*.ts', '*.tsx', '*.js', '*.jsx', '*.java', '*.cs', '*.go', '*.rs', '*.cpp', '*.c', '*.h']
    
    for ext in source_extensions:
        count += sum(1 for _ in project_path.rglob(ext))
    
    return count


def is_target_project_indexed() -> bool:
    """
    Check if the target project has been indexed in RAG.
    
    Returns:
        True if indexed, False otherwise
    """
    try:
        from backend.services.rag_retriever import get_retriever
        
        retriever = get_retriever()
        if hasattr(retriever, 'collection') and retriever.collection:
            count = retriever.collection.count()
            return count > 0
        return False
    except Exception:
        return False


# Expose main function for easy import
__all__ = [
    "get_target_project_path",
    "get_available_projects",
    "score_directory",
    "get_target_project_name",
    "get_target_project_info",
    "detect_tech_stack",
    "detect_project_markers",
    "count_source_files",
    "is_target_project_indexed"
]
