"""
Migration script to consolidate legacy timestamped version files into stable artifact IDs.
"""
import json
import re
from pathlib import Path

def migrate():
    versions_dir = Path('data/versions')
    if not versions_dir.exists():
        print("No versions directory found")
        return
    
    timestamp_pattern = re.compile(r'^(.+)_(\d{8}_\d{6})$')

    # Group legacy artifacts by base type
    legacy_groups = {}
    stable_ids = []

    for f in versions_dir.glob('*.json'):
        artifact_id = f.stem
        match = timestamp_pattern.match(artifact_id)
        if match:
            base_type = match.group(1)
            if base_type not in legacy_groups:
                legacy_groups[base_type] = []
            legacy_groups[base_type].append(artifact_id)
        else:
            stable_ids.append(artifact_id)

    if not legacy_groups:
        print("No legacy artifacts to migrate!")
        print(f"Stable artifacts: {stable_ids}")
        return

    print(f'Found {len(legacy_groups)} legacy groups to migrate:')
    for base_type, ids in legacy_groups.items():
        print(f'  {base_type}: {len(ids)} artifacts')

    print(f'Already stable: {stable_ids}')

    # Migrate each group
    for base_type, legacy_ids in legacy_groups.items():
        legacy_ids.sort()  # Sort by timestamp
        
        all_versions = []
        for legacy_id in legacy_ids:
            legacy_file = versions_dir / f'{legacy_id}.json'
            with open(legacy_file, 'r', encoding='utf-8') as f:
                versions = json.load(f)
                for v in versions:
                    v['metadata'] = v.get('metadata', {})
                    v['metadata']['migrated_from'] = legacy_id
                    all_versions.append(v)
        
        # Sort by created_at
        all_versions.sort(key=lambda v: v.get('created_at', ''))
        
        # Renumber versions
        for i, v in enumerate(all_versions):
            v['version'] = i + 1
            v['artifact_id'] = base_type
            v['is_current'] = (i == len(all_versions) - 1)
        
        # Save consolidated file
        consolidated_file = versions_dir / f'{base_type}.json'
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            json.dump(all_versions, f, indent=2, default=str)
        print(f'Created {consolidated_file} with {len(all_versions)} versions')
        
        # Delete legacy files
        for legacy_id in legacy_ids:
            legacy_file = versions_dir / f'{legacy_id}.json'
            legacy_file.unlink()
            print(f'  Deleted {legacy_file}')

    print('\n✅ Migration complete!')
    print(f'All versions now use stable artifact IDs.')
    print(f'Versions are numbered v1, v2, v3, etc. within each artifact type.')

if __name__ == '__main__':
    migrate()

