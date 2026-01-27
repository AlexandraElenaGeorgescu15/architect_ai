import sys
from pathlib import Path

# Add current dir to path
sys.path.insert(0, str(Path.cwd()))

from backend.utils.tool_detector import detect_tool_directory
from backend.utils.target_project import get_available_projects, _score_directory, detect_project_markers, get_target_project_path

def verify():
    tool_dir = detect_tool_directory()
    print(f"Tool Directory: {tool_dir}")
    
    if tool_dir:
        parent = tool_dir.parent
        print(f"Parent Directory: {parent}")
        
        current_target = get_target_project_path()
        print(f"Current Target Project: {current_target}")
        
        available_projects = get_available_projects()
        print(f"Available Projects: {len(available_projects)}")
        
        for d in available_projects:
            print(f"Checking {d}:")
            print(f"  - Exists: {d.exists()}")
            print(f"  - Is Dir: {d.is_dir()}")
            print(f"  - Is Tool Dir: {d.resolve() == tool_dir.resolve()}")
            print(f"  - Score: {_score_directory(d)}")
            print(f"  - Markers: {detect_project_markers(d)}")
    else:
        print("Tool directory not detected!")

if __name__ == "__main__":
    verify()
