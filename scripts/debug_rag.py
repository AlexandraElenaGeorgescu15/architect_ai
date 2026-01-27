
import asyncio
import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.rag_ingester import RAGIngester
from backend.utils.tool_detector import detect_tool_directory
from backend.core.logger import get_logger

# Configure logging to show debug output to console
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("backend.services.rag_ingester")
logger.setLevel(logging.DEBUG)

async def debug_indexing():
    print("🚀 Starting RAG Debug Script")
    tool_dir = detect_tool_directory()
    print(f"🕵️ Detected Tool Directory: {tool_dir}")
    
    ingester = RAGIngester()
    
    # Test paths
    paths_to_test = [
        Path(r"C:\Users\AGEORGE2\Desktop\Dawn-final-project\final_project"),
        Path(r"C:\Users\AGEORGE2\Desktop\Dawn-final-project\final-proj-sln")
    ]
    
    for path in paths_to_test:
        print(f"\n📂 Testing directory: {path}")
        if not path.exists():
            print(f"❌ Path does not exist: {path}")
            continue
            
        print("   Running index_directory...")
        stats = await ingester.index_directory(path, recursive=True)
        print(f"   📊 Stats: {stats}")

    # Verify Retriever view
    print("\n🔍 Verifying RAGRetriever view...")
    from backend.services.rag_retriever import get_retriever
    retriever = get_retriever()
    count = retriever.collection.count()
    print(f"   Retriever reports {count} documents in collection")
    
    # Check if we can search
    results = retriever.vector_search("user controller", k=1)
    print(f"   Test Search Results: {len(results)}")


if __name__ == "__main__":
    asyncio.run(debug_indexing())
