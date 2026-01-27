
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

def debug_detection():
    print("Debugging Project Detection Logic...")
    
    try:
        from components._tool_detector import get_user_project_directories, detect_tool_directory
        
        tool_dir = detect_tool_directory()
        print(f"Detected Tool Directory: {tool_dir}")
        
        projects = get_user_project_directories()
        print(f"Found {len(projects)} User Projects:")
        for p in projects:
            print(f"  - {p} {'(TOOL)' if p == tool_dir else ''}")
            
        # Check parent directory explicitly
        cwd = Path.cwd()
        parent = cwd.parent
        print(f"\nChecking Parent Directory: {parent}")
        print(f"   Contents: {[x.name for x in parent.iterdir() if x.is_dir()]}")
        
    except Exception as e:
        print(f"❌ Error during detection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_detection()
