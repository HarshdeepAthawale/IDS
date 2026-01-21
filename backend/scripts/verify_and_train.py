#!/usr/bin/env python3
"""
Verify MongoDB import status and proceed with training if ready
"""

import os
import sys
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.data_collector import DataCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_import():
    """Verify MongoDB import status"""
    try:
        config = Config()
        collector = DataCollector(config)
        stats = collector.get_statistics()
        
        total = stats.get('total_samples', 0)
        benign = stats.get('benign_count', 0)
        malicious = stats.get('malicious_count', 0)
        
        print("\n" + "="*60)
        print("MongoDB Import Status")
        print("="*60)
        print(f"Total samples: {total:,}")
        print(f"Benign: {benign:,}")
        print(f"Malicious: {malicious:,}")
        print("="*60 + "\n")
        
        # Check if we have sufficient samples
        if total >= 1000 and benign > 0 and malicious > 0:
            logger.info("✓ Import verification passed - ready for training")
            return True
        elif total > 0:
            logger.warning(f"⚠ Import incomplete or unbalanced: {total:,} samples")
            logger.warning(f"  Benign: {benign:,}, Malicious: {malicious:,}")
            return False
        else:
            logger.error("✗ No samples found in database")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error verifying import: {e}")
        logger.error("Make sure MongoDB is running!")
        return False


if __name__ == '__main__':
    if verify_import():
        print("\nProceeding to training...")
        print("Run: python scripts/train_from_cicids2018.py")
        sys.exit(0)
    else:
        print("\nImport verification failed. Please check MongoDB status.")
        sys.exit(1)
