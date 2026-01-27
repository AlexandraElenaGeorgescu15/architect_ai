
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock Pydantic models needed for the logic
class UserPublic(BaseModel):
    id: str = "test-user"
    email: str = "test@example.com"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.api.chat")

from backend.core.config import settings
from backend.services.rag_retriever import get_retriever
from backend.utils.tool_detector import get_user_project_directories, detect_tool_directory
from backend.services.multi_repo import get_multi_repo_service

async def debug_summary_logic():
    print("🚀 Debugging Project Summary Logic")
    
    # =================================================================
    # LOGIC COPIED FROM backend/api/chat.py
    # =================================================================
    
    # Get ALL user projects (excludes Architect.AI and utility folders)
    user_project_dirs = get_user_project_directories()
    tool_dir = detect_tool_directory()
    print(f"🧐 [DEBUG_SUMMARY] Tool Dir: {tool_dir}")
    print(f"🧐 [DEBUG_SUMMARY] Raw User Dirs: {user_project_dirs}")
    
    # Folders that should never appear as user projects
    EXCLUDED_FOLDER_NAMES = {
        'agents', 'components', 'utils', 'shared', 'common', 'lib', 'libs',
        'node_modules', '__pycache__', '.git', 'dist', 'build', 'bin', 'obj',
        'archive', 'backup', 'temp', 'tmp', 'cache', '.cache', 'logs',
    }
    
    # Filter out tool directory and excluded folders
    user_project_dirs = [
        d for d in user_project_dirs 
        if d != tool_dir 
        and 'architect_ai' not in str(d).lower()
        and d.name.lower() not in EXCLUDED_FOLDER_NAMES
    ]
    print(f"🧐 [DEBUG_SUMMARY] Filtered User Dirs: {user_project_dirs}")
    
    # Get RAG stats with PER-PROJECT BREAKDOWN
    rag_retriever = get_retriever()
    indexed_files = 0
    
    try:
        # Get index stats from ChromaDB
        index_path = Path(settings.rag_index_path if hasattr(settings, 'rag_index_path') else "rag/index")
        print(f"🧐 [DEBUG_SUMMARY] RAG Index Path: {index_path} (Exists: {index_path.exists()})")
        
        if index_path.exists():
            # Count files in ChromaDB collection
            if hasattr(rag_retriever, 'collection') and rag_retriever.collection:
                indexed_files = rag_retriever.collection.count()
                print(f"🧐 [DEBUG_SUMMARY] Collection Count: {indexed_files}")
            else:
                print("❌ rag_retriever.collection is None or missing")
            
            # FIX: Check MultiRepoService for repo-specific indices
            try:
                multi_repo = get_multi_repo_service()
                repos = multi_repo.get_repositories()
                print(f"multi_repo reps: {repos}")
            except Exception as e:
                print(f"Multi repo error: {e}")

    except Exception as e:
        print(f"Error getting stats: {e}")

if __name__ == "__main__":
    asyncio.run(debug_summary_logic())
