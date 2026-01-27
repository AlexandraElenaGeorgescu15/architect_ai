
import sys
import os
import asyncio
import json

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

async def check_project_coverage():
    print("Checking if user projects are in RAG index...")
    
    try:
        from backend.services.rag_ingester import get_ingester
        ingester = get_ingester()
        
        # Access internal hashes directly for debugging
        hashes = ingester.file_hashes
        print(f"Total tracked files: {len(hashes)}")
        
        final_project_files = [f for f in hashes.keys() if "final_project" in f]
        sln_files = [f for f in hashes.keys() if "final-proj-sln" in f]
        
        print(f"\n'final_project' files indexed: {len(final_project_files)}")
        if len(final_project_files) > 0:
            print(f"Sample: {final_project_files[:3]}")
            
        print(f"\n'final-proj-sln' files indexed: {len(sln_files)}")
        if len(sln_files) > 0:
            print(f"Sample: {sln_files[:3]}")
            
        if len(final_project_files) == 0 and len(sln_files) == 0:
            print("\n❌ User projects are NOT indexed.")
        else:
            print("\n✅ At least some user project files are indexed.")
            
    except Exception as e:
        print(f"Error checking coverage: {e}")

if __name__ == "__main__":
    asyncio.run(check_project_coverage())
