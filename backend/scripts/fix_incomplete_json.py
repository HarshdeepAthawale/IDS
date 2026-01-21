#!/usr/bin/env python3
"""
Fix incomplete JSON file from interrupted preprocessing
"""

import json
import sys
from pathlib import Path

def fix_incomplete_json(json_file: Path, backup: bool = True):
    """Fix incomplete JSON file by removing trailing comma and closing array"""
    
    if not json_file.exists():
        print(f"Error: File not found: {json_file}")
        return False
    
    # Backup original file
    if backup:
        backup_file = json_file.with_suffix('.json.backup')
        print(f"Creating backup: {backup_file}")
        import shutil
        shutil.copy2(json_file, backup_file)
    
    print(f"Reading file: {json_file}")
    print(f"File size: {json_file.stat().st_size / (1024**3):.2f} GB")
    
    # Read file content
    with open(json_file, 'r') as f:
        content = f.read()
    
    # Remove trailing whitespace
    content = content.rstrip()
    
    # Check if it ends properly
    if content.endswith(']'):
        print("✓ JSON file appears complete")
        return True
    
    # Fix incomplete JSON
    print("Fixing incomplete JSON...")
    
    # Remove trailing comma if present
    if content.endswith(','):
        content = content[:-1]
    
    # Ensure it ends with ]
    if not content.endswith(']'):
        content = content.rstrip() + '\n]'
    
    # Write fixed content
    print("Writing fixed JSON...")
    with open(json_file, 'w') as f:
        f.write(content)
    
    # Validate
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        print(f"✓ JSON file fixed successfully!")
        print(f"Total samples: {len(data)}")
        return True
    except json.JSONDecodeError as e:
        print(f"✗ JSON file still invalid: {e}")
        print("You may need to manually fix the file or restart preprocessing")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix incomplete JSON file')
    parser.add_argument('--json-file', type=str, 
                       default='./data/cicids2018_preprocessed.json',
                       help='Path to JSON file')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip creating backup')
    
    args = parser.parse_args()
    
    json_file = Path(args.json_file)
    success = fix_incomplete_json(json_file, backup=not args.no_backup)
    
    sys.exit(0 if success else 1)
