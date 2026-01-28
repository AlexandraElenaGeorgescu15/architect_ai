"""
Git Service - Provides git diff functionality for artifacts.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import subprocess
import json

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.logger import get_logger
from components._tool_detector import get_user_project_directories
from backend.utils.target_project import get_target_project_path

logger = get_logger(__name__)


class GitService:
    """
    Service for git operations on artifacts.
    
    Features:
    - Get git diff for artifact files
    - Get git history for artifacts
    - Check if file is tracked in git
    - Get git status for artifacts
    """
    
    def __init__(self):
        """Initialize Git Service."""
        self.outputs_dir = Path("outputs")
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Git Service initialized")
    
    def _get_repo_root(self) -> Optional[Path]:
        """Get the git repository root directory."""
        try:
            # Priority 1: Use the standardized target project path
            target_path = get_target_project_path()
            if target_path:
                # Ensure it's a git repo or check its parents
                current = target_path.resolve()
                while current != current.parent:
                    if (current / ".git").exists():
                        return current
                    current = current.parent
            
            # Priority 2: Try to find git repo in auto-detected user directories
            user_dirs = get_user_project_directories()
            for user_dir in user_dirs:
                repo_root = Path(user_dir)
                current = repo_root.resolve()
                while current != current.parent:
                    if (current / ".git").exists():
                        return current
                    current = current.parent
            
            # Fallback: check if outputs directory is in a git repo
            current = self.outputs_dir.resolve()
            while current != current.parent:
                if (current / ".git").exists():
                    return current
                current = current.parent
            
            return None
        except Exception as e:
            logger.debug(f"Could not find git repo: {e}")
            return None
    
    def _run_git_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Run a git command and return success status and output.
        
        Args:
            cmd: Git command as list (e.g., ['git', 'diff', '--stat'])
            cwd: Working directory (defaults to repo root)
        
        Returns:
            (success: bool, output: str)
        """
        repo_root = self._get_repo_root()
        if not repo_root:
            return False, "Not a git repository"
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or repo_root,
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr or result.stdout
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"Error running git command: {e}")
            return False, str(e)
    
    def get_file_git_diff(
        self,
        file_path: str,
        base_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get git diff for a specific file.
        
        Args:
            file_path: Path to the file (relative to repo root or absolute)
            base_ref: Base reference (commit hash, branch, or tag). Defaults to HEAD~1
        
        Returns:
            Dictionary with diff information
        """
        repo_root = self._get_repo_root()
        if not repo_root:
            return {
                "error": "Not a git repository",
                "diff": "",
                "stats": {}
            }
        
        # Resolve file path
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            # Try relative to repo root
            full_path = repo_root / file_path
        else:
            full_path = file_path_obj
        
        # Check if file exists
        if not full_path.exists():
            return {
                "error": f"File not found: {file_path}",
                "diff": "",
                "stats": {}
            }
        
        # Get relative path from repo root
        try:
            rel_path = full_path.relative_to(repo_root)
        except ValueError:
            # File is outside repo
            return {
                "error": f"File is outside git repository: {file_path}",
                "diff": "",
                "stats": {}
            }
        
        # Check if file is tracked in git
        success, status_output = self._run_git_command(
            ['git', 'ls-files', '--error-unmatch', str(rel_path)],
            cwd=repo_root
        )
        
        is_tracked = success
        
        # Get diff
        if base_ref:
            diff_cmd = ['git', 'diff', base_ref, 'HEAD', '--', str(rel_path)]
        else:
            # Show unstaged changes
            diff_cmd = ['git', 'diff', '--', str(rel_path)]
        
        success, diff_output = self._run_git_command(diff_cmd, cwd=repo_root)
        
        # Get diff stats
        stats_cmd = ['git', 'diff', '--stat', '--', str(rel_path)]
        if base_ref:
            stats_cmd = ['git', 'diff', '--stat', base_ref, 'HEAD', '--', str(rel_path)]
        
        success_stats, stats_output = self._run_git_command(stats_cmd, cwd=repo_root)
        
        # Parse stats
        stats = self._parse_diff_stats(stats_output)
        
        return {
            "file_path": str(rel_path),
            "absolute_path": str(full_path),
            "is_tracked": is_tracked,
            "diff": diff_output if success else "",
            "stats": stats,
            "error": None if success else diff_output
        }
    
    def _parse_diff_stats(self, stats_output: str) -> Dict[str, Any]:
        """Parse git diff --stat output."""
        if not stats_output or not stats_output.strip():
            return {
                "additions": 0,
                "deletions": 0,
                "files_changed": 0
            }
        
        lines = stats_output.strip().split('\n')
        if not lines:
            return {
                "additions": 0,
                "deletions": 0,
                "files_changed": 0
            }
        
        # Last line contains summary: "1 file changed, 5 insertions(+), 2 deletions(-)"
        last_line = lines[-1]
        
        additions = 0
        deletions = 0
        files_changed = 0
        
        try:
            # Extract numbers
            if 'insertions' in last_line or 'insertion' in last_line:
                import re
                ins_match = re.search(r'(\d+)\s+insertion', last_line)
                if ins_match:
                    additions = int(ins_match.group(1))
            
            if 'deletions' in last_line or 'deletion' in last_line:
                import re
                del_match = re.search(r'(\d+)\s+deletion', last_line)
                if del_match:
                    deletions = int(del_match.group(1))
            
            if 'file' in last_line:
                import re
                file_match = re.search(r'(\d+)\s+file', last_line)
                if file_match:
                    files_changed = int(file_match.group(1))
        except Exception as e:
            logger.debug(f"Error parsing diff stats: {e}")
        
        return {
            "additions": additions,
            "deletions": deletions,
            "files_changed": files_changed,
            "raw": stats_output
        }
    
    def get_artifact_git_status(self, artifact_id: str) -> Dict[str, Any]:
        """
        Get git status for an artifact.
        
        Args:
            artifact_id: Artifact identifier
        
        Returns:
            Dictionary with git status information
        """
        repo_root = self._get_repo_root()
        if not repo_root:
            return {
                "is_repo": False,
                "status": "not_a_repo"
            }
        
        # Try to find artifact file in outputs directory
        artifact_files = list(self.outputs_dir.rglob(f"*{artifact_id}*"))
        
        if not artifact_files:
            return {
                "is_repo": True,
                "status": "file_not_found",
                "files": []
            }
        
        results = []
        for artifact_file in artifact_files:
            try:
                rel_path = artifact_file.relative_to(repo_root)
            except ValueError:
                # File outside repo
                results.append({
                    "path": str(artifact_file),
                    "status": "outside_repo"
                })
                continue
            
            # Check git status
            success, status_output = self._run_git_command(
                ['git', 'status', '--porcelain', '--', str(rel_path)],
                cwd=repo_root
            )
            
            git_status = "untracked"
            if success and status_output.strip():
                # Parse status: " M file" = modified, "?? file" = untracked, "A  file" = added
                status_code = status_output.strip().split()[0] if status_output.strip() else ""
                if status_code.startswith('??'):
                    git_status = "untracked"
                elif 'M' in status_code:
                    git_status = "modified"
                elif 'A' in status_code:
                    git_status = "added"
                elif 'D' in status_code:
                    git_status = "deleted"
            
            # Check if tracked
            success_tracked, _ = self._run_git_command(
                ['git', 'ls-files', '--error-unmatch', str(rel_path)],
                cwd=repo_root
            )
            
            if success_tracked and git_status == "untracked":
                git_status = "tracked"
            
            results.append({
                "path": str(rel_path),
                "absolute_path": str(artifact_file),
                "status": git_status
            })
        
        return {
            "is_repo": True,
            "status": "ok",
            "files": results
        }
    
    def get_all_artifacts_git_status(self) -> Dict[str, Any]:
        """
        Get git status for all artifacts in outputs directory.
        
        Returns:
            Dictionary mapping artifact files to their git status
        """
        repo_root = self._get_repo_root()
        if not repo_root:
            return {
                "is_repo": False,
                "artifacts": []
            }
        
        # Find all artifact files
        artifact_files = []
        for pattern in ['*.md', '*.mermaid', '*.mmd', '*.html', '*.json', '*.txt']:
            artifact_files.extend(self.outputs_dir.rglob(pattern))
        
        results = []
        for artifact_file in artifact_files:
            try:
                rel_path = artifact_file.relative_to(repo_root)
            except ValueError:
                continue
            
            # Get git status
            success, status_output = self._run_git_command(
                ['git', 'status', '--porcelain', '--', str(rel_path)],
                cwd=repo_root
            )
            
            git_status = "untracked"
            if success and status_output.strip():
                status_code = status_output.strip().split()[0] if status_output.strip() else ""
                if status_code.startswith('??'):
                    git_status = "untracked"
                elif 'M' in status_code:
                    git_status = "modified"
                elif 'A' in status_code:
                    git_status = "added"
            
            # Check if tracked
            success_tracked, _ = self._run_git_command(
                ['git', 'ls-files', '--error-unmatch', str(rel_path)],
                cwd=repo_root
            )
            
            if success_tracked and git_status == "untracked":
                git_status = "tracked"
            
            results.append({
                "file": str(rel_path),
                "absolute_path": str(artifact_file),
                "status": git_status,
                "name": artifact_file.name
            })
        
        return {
            "is_repo": True,
            "artifacts": results
        }


# Global service instance
_git_service: Optional[GitService] = None


def get_git_service() -> GitService:
    """Get or create global Git Service instance."""
    global _git_service
    if _git_service is None:
        _git_service = GitService()
    return _git_service

