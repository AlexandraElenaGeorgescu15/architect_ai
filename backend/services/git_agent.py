import re
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from backend.services.generation_service import get_service as get_gen_service
from backend.services.version_service import get_version_service
from backend.services.git_service import get_git_service

logger = logging.getLogger(__name__)

class GitAgent:
    """
    Autonomous Git Agent responsible for applying generated code prototypes
    to the repository and creating GitHub Pull Requests.
    """
    
    def __init__(self):
        self.gen_service = get_gen_service()
        self.version_service = get_version_service()
        self.git_service = get_git_service()
        # Repo root is determined by git_service
        self.repo_root = self.git_service._get_repo_root()
        
    def parse_code_prototype(self, content: str) -> Dict[str, str]:
        """
        Parse the structured code prototype artifact.
        Expects sections: INTEGRATION PLAN, BACKEND IMPLEMENTATION, FRONTEND IMPLEMENTATION, TESTS.
        """
        sections = {}
        
        # Normalize line endings
        content = content.replace("\r\n", "\n")
        
        # Extract Integration Plan
        plan_match = re.search(r"=== INTEGRATION PLAN ===\n(.*?)\n===", content, re.DOTALL)
        if plan_match:
            sections["plan"] = plan_match.group(1).strip()
            
            # Try to extract Target Files - support both "Backend Target File:" and "- Backend Target:"
            backend_file_match = re.search(r"(?:Backend Target File:|- Backend Target:)\s*(.*?)(\n|$)", sections["plan"])
            if backend_file_match:
                sections["backend_target_file"] = backend_file_match.group(1).strip()
            
            frontend_file_match = re.search(r"(?:Frontend Target File:|- Frontend Target:)\s*(.*?)(\n|$)", sections["plan"])
            if frontend_file_match:
                sections["frontend_target_file"] = frontend_file_match.group(1).strip()
            
            # Legacy fallback
            if not backend_file_match and not frontend_file_match:
                file_match = re.search(r"Target File:\s*(.*?)(\n|$)", sections["plan"])
                if file_match:
                    sections["target_file"] = file_match.group(1).strip()
        
        # Extract Backend Implementation
        backend_impl_match = re.search(r"=== BACKEND IMPLEMENTATION ===\n(.*?)\n===", content, re.DOTALL)
        if backend_impl_match:
            sections["backend_implementation"] = backend_impl_match.group(1).strip()
        
        # Extract Frontend Implementation
        frontend_impl_match = re.search(r"=== FRONTEND IMPLEMENTATION ===\n(.*?)\n===", content, re.DOTALL)
        if frontend_impl_match:
            sections["frontend_implementation"] = frontend_impl_match.group(1).strip()
            
        # Legacy fallback for single implementation
        if not backend_impl_match and not frontend_impl_match:
            impl_match = re.search(r"=== IMPLEMENTATION ===\n(.*?)\n===", content, re.DOTALL)
            if impl_match:
                sections["implementation"] = impl_match.group(1).strip()
            else:
                impl_match = re.search(r"=== IMPLEMENTATION ===\n(.*)", content, re.DOTALL)
                if impl_match:
                    sections["implementation"] = impl_match.group(1).strip()
            
        # Extract Tests
        tests_match = re.search(r"=== TESTS ===\n(.*?)\n=== END ===", content, re.DOTALL)
        if tests_match:
            sections["tests"] = tests_match.group(1).strip()
        elif "=== TESTS ===" in content:
            # If end marker missing
            parts = content.split("=== TESTS ===")
            if len(parts) > 1:
                sections["tests"] = parts[1].split("=== END ===")[0].strip()
            
        return sections

    def _run_git(self, args: List[str]) -> str:
        """Run a git command in the repo root."""
        if not self.repo_root:
            raise Exception("Not a git repository")
            
        result = subprocess.run(
            ["git"] + args,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8"
        )
        if result.returncode != 0:
            raise Exception(f"Git command failed: {result.stderr}")
        return result.stdout.strip()

    async def apply_prototype_and_push(self, artifact_id: str) -> Dict[str, Any]:
        """
        Main entry point: applies artifact to disk and pushes to GitHub.
        """
        logger.info(f"🤖 [GIT_AGENT] Starting PR process for artifact: {artifact_id}")
        
        # 1. Get Artifact
        artifact = None
        # Try active jobs
        if artifact_id in self.gen_service.active_jobs:
            artifact = self.gen_service.active_jobs[artifact_id].get("artifact")
        
        # Try versions
        if not artifact:
            versions = self.version_service.get_versions(artifact_id)
            if versions:
                artifact = versions[-1] # Latest version
                
        if not artifact:
            raise Exception(f"Artifact {artifact_id} not found")
            
        content = artifact.get("content", "")
        if not content:
            raise Exception("Artifact has no content")
            
        # 2. Parse
        parsed = self.parse_code_prototype(content)
        
        # New split strategy
        backend_file_rel = parsed.get("backend_target_file")
        frontend_file_rel = parsed.get("frontend_target_file")
        backend_impl = parsed.get("backend_implementation")
        frontend_impl = parsed.get("frontend_implementation")
        
        # Legacy fallback
        target_file_rel = parsed.get("target_file")
        implementation = parsed.get("implementation")
        
        tests = parsed.get("tests")
        
        files_to_write = [] # List of (rel_path, content)
        
        if backend_file_rel and backend_impl:
            files_to_write.append((backend_file_rel, backend_impl))
        
        if frontend_file_rel and frontend_impl:
            files_to_write.append((frontend_file_rel, frontend_impl))
            
        if not files_to_write:
            if target_file_rel and implementation:
                files_to_write.append((target_file_rel, implementation))
            else:
                raise Exception("Could not find any implementation sections to apply")
            
        # 3. Create Branch
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_name = f"feature/ai-gen-{timestamp}"
        logger.info(f"🤖 [GIT_AGENT] Creating branch: {branch_name}")
        
        try:
            # Stash any local changes to ensure clean branch
            self._run_git(["stash"])
            self._run_git(["checkout", "-b", branch_name])
            
            # 4. Write Implementations
            written_files = []
            for rel_path, impl_content in files_to_write:
                full_path = self.repo_root / rel_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(impl_content)
                written_files.append(rel_path)
                logger.info(f"🤖 [GIT_AGENT] Wrote implementation to: {rel_path}")
            
            # 5. Write Tests (if any)
            test_file_rel = None
            if tests:
                # Heuristic for test file name - use first written file if target_file_rel missing
                base_ref = target_file_rel if target_file_rel else (written_files[0] if written_files else "implementation.py")
                p = Path(base_ref)
                if p.suffix == ".py":
                    if p.name.startswith("test_"):
                         test_file_rel = str(p) # It IS a test file
                    else:
                         test_file_rel = str(p.parent / f"test_{p.name}")
                elif p.suffix in [".js", ".ts", ".tsx"]:
                    test_file_rel = str(p.parent / f"{p.stem}.test{p.suffix}")
                
                if test_file_rel:
                    test_path = self.repo_root / test_file_rel
                    test_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(test_path, "w", encoding="utf-8") as f:
                        f.write(tests)
                    logger.info(f"🤖 [GIT_AGENT] Wrote tests to: {test_file_rel}")

            # 6. Commit
            self._run_git(["add", "."])
            commit_msg = f"feat: automated implementation from AI prototype\n\nArtifact ID: {artifact_id}"
            self._run_git(["commit", "-m", commit_msg])
            logger.info(f"🤖 [GIT_AGENT] Committed changes")
            
            # 7. Push
            logger.info(f"🤖 [GIT_AGENT] Pushing to origin...")
            try:
                self._run_git(["push", "origin", branch_name])
                push_success = True
            except Exception as e:
                logger.warning(f"🤖 [GIT_AGENT] Push failed: {e}. Maybe remote is not set up correctly.")
                push_success = False

            # 8. Generate PR URL (GitHub specific)
            remote_url = self._run_git(["remote", "get-url", "origin"])
            pr_url = None
            if "github.com" in remote_url:
                # Try to detect if we use main or master
                base_branch = "main"
                try:
                    branches = self._run_git(["branch", "-a"])
                    if "master" in branches and "main" not in branches:
                        base_branch = "master"
                except: pass
                
                # Example: https://github.com/user/repo.git -> https://github.com/user/repo/compare/main...branch
                clean_url = remote_url.replace(".git", "").replace("git@github.com:", "https://github.com/")
                if clean_url.endswith("/"): clean_url = clean_url[:-1]
                pr_url = f"{clean_url}/compare/{base_branch}...{branch_name}?expand=1"

            return {
                "success": True,
                "branch": branch_name,
                "files_updated": written_files + ([test_file_rel] if test_file_rel else []),
                "pushed": push_success,
                "pr_url": pr_url,
                "message": "PR branch created and pushed successfully." if push_success else "Branch created and committed locally, but push failed."
            }
            
        except Exception as e:
            logger.error(f"🤖 [GIT_AGENT] Error in PR process: {e}")
            # Try to return to main branch
            try:
                self._run_git(["checkout", "main"])
                self._run_git(["stash", "pop"])
            except: pass
            return {
                "success": False,
                "error": str(e)
            }

# Singleton
_git_agent = None

def get_git_agent() -> GitAgent:
    global _git_agent
    if _git_agent is None:
        _git_agent = GitAgent()
    return _git_agent
