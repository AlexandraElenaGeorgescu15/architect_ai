
import sys
import os
import asyncio
import logging

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO)

async def trigger_reindex():
    print("Triggering User Project Reindex...")
    
    try:
        from backend.services.rag_ingester import get_ingester
        from backend.utils.tool_detector import get_user_project_directories
        
        ingester = get_ingester()
        projects = get_user_project_directories()
        
        print(f"Found {len(projects)} projects:")
        for p in projects:
            print(f"  - {p}")
            
        print("\nStarting indexing...")
        for p in projects:
            print(f"  > Indexing {p}...")
            stats = await ingester.index_directory(p, recursive=True)
            print(f"    Done. Stats: {stats}")
            
            # Start watching it too
            ingester.start_watching(p)
            print(f"    Started watching {p}")
            
        print("\nReindex logic complete.")
        
    except Exception as e:
        print(f"Error during reindex: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(trigger_reindex())
