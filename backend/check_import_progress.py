#!/usr/bin/env python3
"""Check MongoDB import progress"""
import sys
from config import Config
from services.data_collector import DataCollector

try:
    config = Config()
    data_collector = DataCollector(config)
    
    stats = data_collector.get_statistics()
    
    print("="*60)
    print("Import Progress")
    print("="*60)
    print(f"Total samples: {stats.get('total_samples', 0):,}")
    print(f"Labeled samples: {stats.get('labeled_samples', 0):,}")
    print(f"  - Benign: {stats.get('benign_count', 0):,}")
    print(f"  - Malicious: {stats.get('malicious_count', 0):,}")
    print(f"CICIDS2018 imported: {stats.get('cicids2018_imported', 0):,}")
    print("="*60)
    
    # Estimate progress (target: ~8M samples)
    total = stats.get('total_samples', 0)
    target = 8_034_453
    if total > 0:
        progress = (total / target) * 100
        print(f"Progress: {progress:.2f}% ({total:,} / {target:,})")
        remaining = target - total
        if remaining > 0:
            print(f"Remaining: {remaining:,} samples")
    
    sys.exit(0)
except Exception as e:
    print(f"Error checking progress: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
