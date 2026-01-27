
import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils.tool_detector import detect_tool_directory, should_exclude_path

def debug_tool_detection():
    print("🚀 Debugging Tool Detection")
    
    # Check what directory is detected as the tool
    tool_dir = detect_tool_directory()
    print(f"🕵️ Detected Tool Directory: {tool_dir}")
    
    # Test exclusion on a user file
    user_file = Path(r"C:\Users\AGEORGE2\Desktop\Dawn-final-project\final_project\.vscode\extensions.json")
    is_excluded = should_exclude_path(user_file)
    print(f"🧪 Testing file: {user_file}")
    print(f"🚫 Is Excluded? {is_excluded}")
    
    if tool_dir:
        try:
            rel = user_file.resolve().relative_to(tool_dir.resolve())
            print(f"   Relative to tool dir: {rel} (matches!)")
        except ValueError:
            print(f"   Relative to tool dir: Not relative (mismatch)")

if __name__ == "__main__":
    debug_tool_detection()
