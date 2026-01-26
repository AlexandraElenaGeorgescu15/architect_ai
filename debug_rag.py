import sys
from pathlib import Path
import asyncio

# Add current dir to path
sys.path.insert(0, str(Path.cwd()))

from backend.services.rag_ingester import get_ingester
from backend.utils.tool_detector import get_user_project_directories

async def main():
    ing = get_ingester()
    
    print("--- RAG Status ---")
    stats = ing.get_index_stats()
    print(f"Total chunks: {stats.get('total_chunks', 0)}")
    print(f"Tracked files: {stats.get('file_hashes_tracked', 0)}")
    
    user_dirs = get_user_project_directories()
    print(f"Indexing directories: {[str(d) for d in user_dirs]}")
    
    for directory in user_dirs:
        print(f"Indexing {directory}...")
        res = await ing.index_directory(directory)
        print(f"Result for {directory.name}: {res}")

if __name__ == "__main__":
    asyncio.run(main())
