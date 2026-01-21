#!/usr/bin/env python3
"""
Check preprocessing progress from log files and checkpoint
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def check_progress():
    """Check preprocessing progress"""
    checkpoint_file = Path('preprocessing_checkpoint.json')
    log_file = Path('preprocessing.log')
    output_file = Path('data/cicids2018_preprocessed.json')
    
    print("="*60)
    print("Preprocessing Progress Check")
    print("="*60)
    
    # Check if process is running
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'preprocess_cicids2018.py'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Preprocessing process is running")
    else:
        print("✗ Preprocessing process not running")
    
    # Check checkpoint
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
            print(f"\nCheckpoint Status:")
            print(f"  Files completed: {len(checkpoint.get('files_completed', []))}")
            print(f"  Last file: {checkpoint.get('last_file', 'N/A')}")
            print(f"  Total samples: {checkpoint.get('total_samples', 0):,}")
            print(f"  Benign: {checkpoint.get('total_benign', 0):,}")
            print(f"  Malicious: {checkpoint.get('total_malicious', 0):,}")
            print(f"  Last update: {checkpoint.get('last_update', 'N/A')}")
        except Exception as e:
            print(f"  Error reading checkpoint: {e}")
    else:
        print("\nNo checkpoint file found (processing from start)")
    
    # Check output file
    if output_file.exists():
        size_gb = output_file.stat().st_size / (1024**3)
        print(f"\nOutput File:")
        print(f"  Exists: Yes")
        print(f"  Size: {size_gb:.2f} GB")
        
        # Try to get sample count (quick check)
        try:
            with open(output_file, 'r') as f:
                # Read first few lines to check structure
                first_line = f.readline()
                if first_line.strip() == '[':
                    # Count samples by counting opening braces (rough estimate)
                    f.seek(0)
                    content = f.read(1000000)  # Read first 1MB
                    sample_count = content.count('"label"')
                    if sample_count > 0:
                        print(f"  Estimated samples (from first 1MB): ~{sample_count}")
        except Exception as e:
            print(f"  Could not estimate sample count: {e}")
    else:
        print(f"\nOutput File: Not created yet")
    
    # Check log file
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    print(f"\nLast Log Entry:")
                    print(f"  {last_line}")
        except Exception as e:
            print(f"  Error reading log: {e}")
    
    print("="*60)
    print("\nExpected: ~8,034,450 samples total")
    print("Processing time: 2-4 hours estimated")

if __name__ == '__main__':
    check_progress()
