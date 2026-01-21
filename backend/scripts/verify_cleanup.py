#!/usr/bin/env python3
"""
Verify MongoDB training_data collection after cleanup
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.data_collector import DataCollector
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    config = Config()
    collector = DataCollector(config)
    
    stats = collector.get_statistics()
    
    total = stats.get('total_samples', 0)
    benign = stats.get('benign_count', 0)
    malicious = stats.get('malicious_count', 0)
    
    print("="*60)
    print("Cleanup Verification")
    print("="*60)
    print(f"Total samples: {total:,}")
    print(f"Benign: {benign:,}")
    print(f"Malicious: {malicious:,}")
    
    if total > 0:
        benign_pct = (benign / total) * 100
        malicious_pct = (malicious / total) * 100
        print(f"\nRatio: {benign_pct:.1f}% benign, {malicious_pct:.1f}% malicious")
        
        # Check targets
        target_total = 37751
        target_benign = 22651
        target_malicious = 15100
        
        print(f"\nTarget: {target_total:,} total ({target_benign:,} benign, {target_malicious:,} malicious)")
        
        if abs(total - target_total) < 1000 and abs(benign - target_benign) < 100:
            print("✓ Cleanup successful!")
        else:
            print("⚠ Cleanup may not be complete")
    
    print("="*60)

if __name__ == '__main__':
    main()
