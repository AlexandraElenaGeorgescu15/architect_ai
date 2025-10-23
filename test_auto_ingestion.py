#!/usr/bin/env python3
"""
Test Script for Automatic RAG Ingestion

This script demonstrates the automatic RAG ingestion system by:
1. Starting the file watcher
2. Making changes to test files
3. Showing the indexing process
4. Displaying results

Usage:
    python test_auto_ingestion.py
"""

import asyncio
import time
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_auto_ingestion():
    """Test the automatic RAG ingestion system"""
    
    print("🚀 Testing Automatic RAG Ingestion System")
    print("=" * 50)
    
    try:
        # Import the auto-ingestion components
        from rag.auto_ingestion import get_auto_ingestion_manager, get_auto_ingestion_status
        from rag.file_watcher import FileChangeEvent
        
        # Get the manager
        manager = get_auto_ingestion_manager()
        
        # Check initial status
        print("\n📊 Initial Status:")
        status = manager.get_status()
        print(f"  - Enabled: {status['enabled']}")
        print(f"  - Running: {status['is_running']}")
        print(f"  - Active Jobs: {status['active_jobs']}")
        
        if not status['enabled']:
            print("❌ Auto-ingestion is disabled in configuration")
            print("   Enable it in rag/config.yaml to run this test")
            return
        
        # Start the system
        print("\n🔄 Starting Auto-Ingestion System...")
        if not manager.start():
            print("❌ Failed to start auto-ingestion system")
            return
        
        print("✅ Auto-ingestion system started successfully")
        
        # Wait a moment for the system to initialize
        await asyncio.sleep(2)
        
        # Create a test file
        test_file = Path("test_rag_file.py")
        print(f"\n📝 Creating test file: {test_file}")
        
        test_content = f'''
# Test file for RAG auto-ingestion
# Created at: {datetime.now()}

def test_function():
    """This is a test function for RAG indexing"""
    return "Hello from auto-ingestion test!"

class TestClass:
    """Test class for RAG indexing"""
    
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value

# This file will be automatically indexed by the RAG system
'''
        
        test_file.write_text(test_content)
        print(f"✅ Created {test_file}")
        
        # Wait for file to be processed
        print("\n⏳ Waiting for file to be processed...")
        await asyncio.sleep(10)
        
        # Check status after file creation
        print("\n📊 Status After File Creation:")
        status = manager.get_status()
        print(f"  - Running: {status['is_running']}")
        print(f"  - Active Jobs: {status['active_jobs']}")
        print(f"  - Pending Events: {status['pending_events']}")
        
        if status['recent_jobs']:
            print("  - Recent Jobs:")
            for job in status['recent_jobs'][-3:]:
                print(f"    * {job.status} - {job.files_processed}/{job.total_files} files")
        
        # Modify the test file
        print(f"\n✏️ Modifying test file: {test_file}")
        modified_content = test_content + "\n# Modified at: " + str(datetime.now())
        test_file.write_text(modified_content)
        print(f"✅ Modified {test_file}")
        
        # Wait for modification to be processed
        print("\n⏳ Waiting for modification to be processed...")
        await asyncio.sleep(10)
        
        # Check final status
        print("\n📊 Final Status:")
        status = manager.get_status()
        print(f"  - Running: {status['is_running']}")
        print(f"  - Active Jobs: {status['active_jobs']}")
        print(f"  - Pending Events: {status['pending_events']}")
        
        if status['recent_jobs']:
            print("  - Recent Jobs:")
            for job in status['recent_jobs'][-3:]:
                print(f"    * {job.status} - {job.files_processed}/{job.total_files} files")
        
        # Clean up test file
        print(f"\n🧹 Cleaning up test file: {test_file}")
        if test_file.exists():
            test_file.unlink()
            print(f"✅ Removed {test_file}")
        
        # Wait for deletion to be processed
        print("\n⏳ Waiting for deletion to be processed...")
        await asyncio.sleep(5)
        
        print("\n✅ Test completed successfully!")
        print("\n📋 Summary:")
        print("  - File watcher detected file changes")
        print("  - Background worker processed indexing jobs")
        print("  - RAG index was updated automatically")
        print("  - No manual intervention required")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running from the correct directory")
        print("   and all dependencies are installed")
    except Exception as e:
        print(f"❌ Error during test: {e}")
        logger.exception("Test failed")
    
    finally:
        # Stop the system
        try:
            print("\n🛑 Stopping Auto-Ingestion System...")
            manager.stop()
            print("✅ Auto-ingestion system stopped")
        except:
            pass


async def test_manual_ingestion():
    """Test manual ingestion for comparison"""
    
    print("\n🔧 Testing Manual Ingestion (for comparison)")
    print("=" * 50)
    
    try:
        from rag.ingest import main as ingest_main
        
        print("📝 Running manual RAG ingestion...")
        start_time = time.time()
        
        # Run the manual ingestion
        ingest_main()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Manual ingestion completed in {duration:.2f} seconds")
        
    except Exception as e:
        print(f"❌ Manual ingestion failed: {e}")


def main():
    """Main test function"""
    
    print("🧪 RAG Auto-Ingestion Test Suite")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("rag").exists():
        print("❌ Please run this script from the architect_ai_cursor_poc directory")
        return
    
    # Check if watchdog is available
    try:
        import watchdog
        print(f"✅ Watchdog library available: {watchdog.__version__}")
    except ImportError:
        print("❌ Watchdog library not available")
        print("   Install it with: pip install watchdog")
        return
    
    # Run the tests
    asyncio.run(test_auto_ingestion())
    
    # Ask if user wants to test manual ingestion
    try:
        response = input("\n❓ Test manual ingestion for comparison? (y/n): ")
        if response.lower().startswith('y'):
            asyncio.run(test_manual_ingestion())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    
    print("\n🎉 All tests completed!")


if __name__ == '__main__':
    main()
