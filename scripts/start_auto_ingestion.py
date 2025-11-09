#!/usr/bin/env python3
"""
Quick Start Script for Automatic RAG Ingestion

This script helps you get the automatic RAG ingestion system running.
It will:
1. Check if auto-ingestion is enabled
2. Start the system if needed
3. Show you the status
4. Provide instructions

Usage:
    python start_auto_ingestion.py
"""

import sys
import asyncio
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import watchdog
        print(f"✅ Watchdog library available: {watchdog.__version__}")
        return True
    except ImportError:
        print("❌ Watchdog library not available")
        print("   Install it with: pip install watchdog")
        return False

def check_configuration():
    """Check if auto-ingestion is enabled in configuration"""
    try:
        from rag.filters import load_cfg
        cfg = load_cfg()
        auto_cfg = cfg.get('auto_ingestion', {})
        enabled = auto_cfg.get('enabled', False)
        
        if enabled:
            print("✅ Auto-ingestion is enabled in configuration")
            print(f"   Watch directories: {auto_cfg.get('watch_directories', ['.'])}")
            print(f"   Debounce seconds: {auto_cfg.get('debounce_seconds', 5)}")
            return True
        else:
            print("⚠️ Auto-ingestion is disabled in configuration")
            print("   Enable it in rag/config.yaml by setting auto_ingestion.enabled: true")
            return False
            
    except Exception as e:
        print(f"❌ Error checking configuration: {e}")
        return False

async def start_system():
    """Start the auto-ingestion system"""
    try:
        from rag.auto_ingestion import get_auto_ingestion_manager
        
        manager = get_auto_ingestion_manager()
        
        if not manager.enabled:
            print("❌ Auto-ingestion is disabled in configuration")
            return False
        
        if manager.is_running:
            print("✅ Auto-ingestion system is already running")
            return True
        
        print("🔄 Starting auto-ingestion system...")
        success = manager.start()
        
        if success:
            print("✅ Auto-ingestion system started successfully!")
            return True
        else:
            print("❌ Failed to start auto-ingestion system")
            return False
            
    except Exception as e:
        print(f"❌ Error starting auto-ingestion system: {e}")
        return False

def show_status():
    """Show current system status"""
    try:
        from rag.auto_ingestion import get_auto_ingestion_status
        
        status = get_auto_ingestion_status()
        
        print("\n📊 Current Status:")
        print(f"  - Enabled: {status['enabled']}")
        print(f"  - Running: {status['is_running']}")
        print(f"  - Active Jobs: {status['active_jobs']}")
        print(f"  - Pending Events: {status['pending_events']}")
        
        if status['file_watcher']:
            watcher = status['file_watcher']
            print(f"  - Watch Directories: {watcher.get('watch_directories', [])}")
            print(f"  - Uptime: {watcher.get('uptime_seconds', 0):.1f} seconds")
        
        if status['recent_jobs']:
            print("  - Recent Jobs:")
            for job in status['recent_jobs'][-3:]:
                print(f"    * {job.status} - {job.files_processed}/{job.total_files} files")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Automatic RAG Ingestion - Quick Start")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("rag").exists():
        print("❌ Please run this script from the architect_ai_cursor_poc directory")
        return
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Check configuration
    if not check_configuration():
        print("\n💡 To enable auto-ingestion:")
        print("   1. Edit rag/config.yaml")
        print("   2. Set auto_ingestion.enabled: true")
        print("   3. Restart the app")
        return
    
    # Start the system
    success = asyncio.run(start_system())
    if not success:
        return
    
    # Show status
    show_status()
    
    print("\n🎉 Auto-ingestion system is now running!")
    print("\n📋 What happens next:")
    print("  - The system will monitor your repository files")
    print("  - When you modify files, they'll be automatically indexed")
    print("  - Check the app sidebar for real-time status")
    print("  - No more manual 'python rag/ingest.py' needed!")
    
    print("\n🧪 To test the system:")
    print("  - Create or modify a file in your repository")
    print("  - Watch the sidebar for indexing activity")
    print("  - Or run: python test_auto_ingestion.py")
    
    print("\n🛑 To stop the system:")
    print("  - Use the pause button in the app sidebar")
    print("  - Or restart the app")

if __name__ == '__main__':
    main()
