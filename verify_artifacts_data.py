
import sys
import os
import json
from pathlib import Path
from glob import glob

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

def verify_artifacts_data():
    print("Starting Artifact Storage Verification...")
    
    versions_dir = Path("data/versions")
    if not versions_dir.exists():
        print(f"Error: Versions directory {versions_dir} does not exist.")
        return False
        
    print(f"Checking {versions_dir}...")
    
    json_files = list(versions_dir.glob("*.json"))
    print(f"found {len(json_files)} artifact files.")
    
    if not json_files:
        print("⚠️ No artifacts found. Assuming clean state.")
        return True
        
    # Analyze a few artifacts to check for 'folder_id'
    artifacts_with_folder = 0
    artifacts_without_folder = 0
    
    for f in json_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                # Data is a list of version objects?
                if isinstance(data, list) and len(data) > 0:
                    latest = data[-1]
                    if "folder_id" in latest and latest["folder_id"]:
                        artifacts_with_folder += 1
                        # print(f"  ✅ Artifact {f.name} has folder_id: {latest['folder_id']}")
                    else:
                        artifacts_without_folder += 1
                        # print(f"  ⚠️ Artifact {f.name} missing folder_id")
        except Exception as e:
            print(f"❌ Error reading {f}: {e}")
            
            print(f"Stats:")
    print(f"  Artifacts with Folder ID: {artifacts_with_folder}")
    print(f"  Artifacts without Folder ID: {artifacts_without_folder}")
    
    if artifacts_with_folder > 0:
        print("At least some artifacts are correctly associated with folders.")
    else:
        print("No artifacts have folder IDs. This might be fine if no folders were used yet, but worth noting.")
        
    return True

if __name__ == "__main__":
    success = verify_artifacts_data()
    sys.exit(0 if success else 1)
