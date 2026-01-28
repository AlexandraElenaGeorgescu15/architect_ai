
import os
import sys
import asyncio
from pathlib import Path

# Add the project root to sys.path
root = Path(r"C:\Users\AGEORGE2\Desktop\Dawn-final-project\architect_ai_cursor_poc")
sys.path.insert(0, str(root))

from backend.services.rag_ingester import get_ingester
from backend.services.universal_context import get_universal_context_service
from backend.utils.tool_detector import get_user_project_directories

async def main():
    print("--- Diagnostic Tool - Project Indexing ---")
    
    ingester = get_ingester()
    uc_service = get_universal_context_service()
    
    # 1. Clear existing index (testing new method)
    print("\n1. Clearing Index...")
    ingester.clear_index()
    stats = ingester.get_index_stats()
    print(f"Stats after clear: {stats}")
    
    # 2. Get projects to index
    projects = get_user_project_directories()
    print(f"\n2. Detected Projects: {[p.name for p in projects]}")
    
    if not projects:
        print("❌ No projects detected!")
        return
    
    # 3. Index one project for test
    test_project = projects[0]
    print(f"\n3. Indexing test project: {test_project.name}...")
    index_stats = await ingester.index_directory(test_project)
    print(f"Indexing Stats: {index_stats}")
    
    # 4. Check global stats
    print("\n4. Final RAG Stats:")
    final_stats = ingester.get_index_stats()
    print(final_stats)
    
    if final_stats.get('total_chunks', 0) > 0:
        print("\n✅ SUCCESS: RAG indexed files!")
    else:
        print("\n❌ FAILURE: RAG still 0 chunks.")
        
    # 5. Build Universal Context
    print("\n5. Building Universal Context...")
    ctx = await uc_service.build_universal_context(force_rebuild=True)
    print(f"Universal Context built_at: {ctx.get('built_at')}")
    print(f"Total Files in Context: {ctx.get('total_files')}")
    
    if ctx.get('total_files', 0) > 0:
        print("✅ SUCCESS: Universal Context has files!")
    else:
        print("❌ FAILURE: Universal Context total_files is 0.")

if __name__ == "__main__":
    # Ensure logs are visible
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
