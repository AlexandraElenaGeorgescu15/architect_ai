
import sys
import os
import shutil
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from backend.services.rag_ingester import get_ingester
from backend.services.rag_retriever import get_retriever

async def verify_external_indexing():
    print("Starting RAG External Indexing Verification...")
    
    # 1. Setup External Directory
    cwd = Path.cwd()
    external_dir = cwd.parent / "test_external_rag_project"
    
    if external_dir.exists():
        shutil.rmtree(external_dir)
    external_dir.mkdir()
    
    print(f"Created external directory: {external_dir}")
    
    # 2. Create Content
    secret_file = external_dir / "secret_project.txt"
    unique_secret = "The flux capacitor requires 1.21 gigawatts of plutonium."
    with open(secret_file, "w") as f:
        f.write(f"CONFIDENTIAL PROJECT ALPHA\n{unique_secret}")
    
    print(f"Created secret file: {secret_file}")
    
    try:
        # 3. Index it
        ingester = get_ingester()
        print(f"⏳ Indexing {external_dir}...")
        
        # We need to ensure we don't accidentally wipe the existing index if that's not desired,
        # but indexing a new directory usually just adds to it.
        # Check if index exists first
        stats = await ingester.index_directory(external_dir, recursive=True)
        print(f"✅ Indexing complete. Stats: {stats}")
        
        if stats["files_indexed"] == 0 and stats["files_skipped"] == 0:
            print("Error: No files were indexed or skipped!")
            return False
            
        if stats["files_skipped"] > 0:
            print("Note: Files were skipped (already indexed). Proceeding to search...")

        # 4. Search for it
        retriever = get_retriever()
        print(f"🔍 Searching for 'flux capacitor'...")
        
        # Give it a moment to commit/flush if needed (Chroma usually handles this)
        await asyncio.sleep(1)
        
        results = retriever.hybrid_search("flux capacitor", k_final=5)
        
        found = False
        for doc, score in results:
            content = doc.get("content", "")
            file_path = doc.get("meta", {}).get("file_path", "")
            
            if unique_secret in content:
                print(f"✅ FOUND MATCH!")
                print(f"   Score: {score}")
                print(f"   File: {file_path}")
                
                # Verify path is correct (should be the external path)
                if str(external_dir) in file_path or str(secret_file) in file_path:
                    print("   ✅ Path is correct (points to external dir)")
                else:
                    print(f"   ❌ Path mismatch! Expected {external_dir} in {file_path}")
                found = True
                break
        
        if not found:
            print("❌ Error: Could not find the secret string in RAG results.")
            print("Top result content:", results[0][0].get("content") if results else "No results")
            return False
            
        print("🎉 RAG External Indexing Verified Successfully!")
        return True

    finally:
        # Cleanup
        if external_dir.exists():
           shutil.rmtree(external_dir)
           print(f"🧹 Cleaned up {external_dir}")

if __name__ == "__main__":
    try:
        # Run async test
        success = asyncio.run(verify_external_indexing())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
