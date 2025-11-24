"""
Tool Detector - Ported from components/_tool_detector.py
Intelligent tool self-detection for automatic exclusion from repo scans.
"""

import sys
from pathlib import Path
from typing import Optional, List, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import from original location (will be refactored later)
from components._tool_detector import (
    detect_tool_directory,
    should_exclude_path,
    get_user_project_directories,
    get_user_project_root
)

__all__ = [
    "detect_tool_directory",
    "should_exclude_path",
    "get_user_project_directories",
    "get_user_project_root"
]

