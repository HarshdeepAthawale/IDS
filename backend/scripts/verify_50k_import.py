#!/usr/bin/env python3
"""
Verify 50K import with 60:40 ratio
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from models.db_models import get_db
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    config = Config()
    db = get_db(config)
    collection = db['training_data']
    
    # Count all samples
    total = collection.count_documents({})
    benign = collection.count_documents({'label': 'benign'})
    malicious = collection.count_documents({'label': {'$ne': 'benign'}})
    
    # Count samples labeled by hackathon_50k
    hackathon_50k_total = collection.count_documents({'labeled_by': 'hackathon_50k'})
    hackathon_50k_benign = collection.count_documents({'label': 'benign', 'labeled_by': 'hackathon_50k'})
    hackathon_50k_malicious = collection.count_documents({'label': {'$ne': 'benign'}, 'labeled_by': 'hackathon_50k'})
    
    print("="*60)
    print("50K Import Verification")
    print("="*60)
    print(f"\n=== All Data in Database ===")
    print(f"Total samples: {total:,}")
    print(f"Benign: {benign:,} ({benign/total*100:.1f}%)")
    print(f"Malicious: {malicious:,} ({malicious/total*100:.1f}%)")
    
    print(f"\n=== Newly Imported 50K Data (hackathon_50k) ===")
    print(f"Total samples: {hackathon_50k_total:,}")
    print(f"Benign: {hackathon_50k_benign:,} ({hackathon_50k_benign/hackathon_50k_total*100:.1f}%)" if hackathon_50k_total > 0 else "Benign: 0")
    print(f"Malicious: {hackathon_50k_malicious:,} ({hackathon_50k_malicious/hackathon_50k_total*100:.1f}%)" if hackathon_50k_total > 0 else "Malicious: 0")
    
    # Verify 50K import
    target_total = 50000
    target_benign = 30000
    target_malicious = 20000
    
    print(f"\n=== Verification ===")
    print(f"Target: {target_total:,} total ({target_benign:,} benign, {target_malicious:,} malicious)")
    
    if hackathon_50k_total == target_total:
        print("✓ Total count matches target (50,000)")
    else:
        print(f"⚠ Total count mismatch: {hackathon_50k_total:,} vs {target_total:,}")
    
    if hackathon_50k_benign == target_benign:
        print("✓ Benign count matches target (30,000)")
    else:
        print(f"⚠ Benign count mismatch: {hackathon_50k_benign:,} vs {target_benign:,}")
    
    if hackathon_50k_malicious == target_malicious:
        print("✓ Malicious count matches target (20,000)")
    else:
        print(f"⚠ Malicious count mismatch: {hackathon_50k_malicious:,} vs {target_malicious:,}")
    
    # Check ratio
    if hackathon_50k_total > 0:
        benign_pct = (hackathon_50k_benign / hackathon_50k_total) * 100
        malicious_pct = (hackathon_50k_malicious / hackathon_50k_total) * 100
        
        if abs(benign_pct - 60.0) < 1.0 and abs(malicious_pct - 40.0) < 1.0:
            print(f"✓ Ratio is correct: {benign_pct:.1f}%:{malicious_pct:.1f}% (target: 60:40)")
        else:
            print(f"⚠ Ratio: {benign_pct:.1f}%:{malicious_pct:.1f}% (target: 60:40)")
    
    print("="*60)
    
    # Summary
    if hackathon_50k_total == target_total and hackathon_50k_benign == target_benign and hackathon_50k_malicious == target_malicious:
        print("\n✓✓✓ 50K Import Verification: SUCCESS ✓✓✓")
        return 0
    else:
        print("\n⚠ 50K Import Verification: Some issues found")
        return 1

if __name__ == '__main__':
    sys.exit(main())
