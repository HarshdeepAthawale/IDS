#!/usr/bin/env python3
"""Quick script to check training data availability"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from services.data_collector import DataCollector

config = Config()
dc = DataCollector(config)
stats = dc.get_statistics()

print("="*60)
print("Training Data Statistics")
print("="*60)
print(f"Total samples: {stats.get('total_samples', 0):,}")
print(f"Labeled samples: {stats.get('labeled_samples', 0):,}")
print(f"Benign: {stats.get('benign_count', 0):,}")
print(f"Malicious: {stats.get('malicious_count', 0):,}")
print("="*60)

if stats.get('labeled_samples', 0) < 1000:
    print("⚠ WARNING: Insufficient labeled samples for training!")
    sys.exit(1)
else:
    print("✓ Sufficient data available for training")
    sys.exit(0)
