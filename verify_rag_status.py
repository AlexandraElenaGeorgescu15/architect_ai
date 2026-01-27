
import sys
import os
import asyncio
import json

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

async def verify_rag_status():
    print("Checking RAG Status...")
    
    try:
        from backend.services.rag_ingester import get_ingester
        ingester = get_ingester()
        stats = ingester.get_index_stats()
        print("\nRAG Stats:")
        print(json.dumps(stats, indent=2))
        
        if stats.get("total_chunks", 0) == 0:
            print("\nWARNING: Total chunks is 0. Index is empty.")
        else:
            print(f"\nIndex contains {stats.get('total_chunks')} chunks.")
            
    except Exception as e:
        print(f"Error checking status: {e}")

if __name__ == "__main__":
    asyncio.run(verify_rag_status())
