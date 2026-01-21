#!/usr/bin/env python3
"""
Export training data from MongoDB to JSON file
Useful for backup or when MongoDB connection is unreliable
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import logging
from datetime import datetime
from decimal import Decimal
import math

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


def clean_value(value: Any) -> Any:
    """Clean value for JSON serialization"""
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (int, float)):
        if math.isinf(value) or math.isnan(value):
            return 0.0
        return float(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: clean_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [clean_value(item) for item in value]
    else:
        return value


def export_samples(data_collector: DataCollector, output_file: Path,
                   label: str = None, batch_size: int = 10000) -> Dict[str, int]:
    """
    Export labeled samples to JSON file
    
    Args:
        data_collector: DataCollector instance
        output_file: Output JSON file path
        label: Filter by label (None for all)
        batch_size: Batch size for processing
    
    Returns:
        Dictionary with export statistics
    """
    stats = {
        'exported': 0,
        'skipped': 0,
        'errors': 0
    }
    
    try:
        logger.info(f"Starting export to {output_file}...")
        
        # Open output file for writing
        with open(output_file, 'w') as f:
            f.write('[\n')  # Start JSON array
            
            first_item = True
            
            # Get batches
            batches = data_collector.get_all_labeled_samples_batch(
                label=label, batch_size=batch_size
            )
            
            try:
                from tqdm import tqdm
                TQDM_AVAILABLE = True
            except ImportError:
                TQDM_AVAILABLE = False
            
            batch_num = 0
            for batch in tqdm(batches, desc="Exporting batches", unit="batch") if TQDM_AVAILABLE else batches:
                batch_num += 1
                
                for sample in batch:
                    try:
                        # Filter by label if specified
                        if label and sample.get('label') != label:
                            stats['skipped'] += 1
                            continue
                        
                        # Clean sample for JSON serialization
                        clean_sample = {
                            'features': clean_value(sample.get('features', {})),
                            'label': sample.get('label'),
                            'labeled_by': sample.get('labeled_by', 'export'),
                            'confidence': float(sample.get('confidence', 1.0)),
                            'source_ip': sample.get('source_ip', 'unknown'),
                            'dest_ip': sample.get('dest_ip', 'unknown'),
                            'protocol': sample.get('protocol', 'unknown'),
                            'dst_port': sample.get('dst_port'),
                            'metadata': clean_value(sample.get('metadata', {}))
                        }
                        
                        # Write JSON object
                        if not first_item:
                            f.write(',\n')
                        json.dump(clean_sample, f)
                        first_item = False
                        
                        stats['exported'] += 1
                        
                        # Flush periodically
                        if stats['exported'] % 1000 == 0:
                            f.flush()
                            
                    except Exception as e:
                        logger.error(f"Error exporting sample: {e}")
                        stats['errors'] += 1
                
                # Log progress
                if batch_num % 10 == 0:
                    logger.info(f"Exported {stats['exported']:,} samples...")
            
            f.write('\n]')  # End JSON array
        
        logger.info(f"Export complete: {stats['exported']:,} exported, "
                   f"{stats['skipped']:,} skipped, {stats['errors']:,} errors")
        
        # Get file size
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        logger.info(f"Output file size: {file_size_mb:.2f} MB")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error during export: {e}")
        import traceback
        traceback.print_exc()
        return stats


def main():
    parser = argparse.ArgumentParser(description='Export training data from MongoDB to JSON')
    parser.add_argument('--output', '-o', type=str, default='training_data_export.json',
                       help='Output JSON file path')
    parser.add_argument('--label', type=str, choices=['benign', 'malicious'],
                       help='Filter by label (optional)')
    parser.add_argument('--batch-size', type=int, default=10000,
                       help='Batch size for processing')
    
    args = parser.parse_args()
    
    logger.info("Training Data Export Script")
    logger.info("="*60)
    
    # Load configuration
    config = Config()
    
    # Initialize data collector
    logger.info("Connecting to MongoDB...")
    data_collector = DataCollector(config)
    
    # Get statistics
    stats = data_collector.get_statistics()
    logger.info("Database Statistics:")
    logger.info(f"  Total samples: {stats.get('total_samples', 0):,}")
    logger.info(f"  Labeled samples: {stats.get('labeled_samples', 0):,}")
    logger.info(f"  Benign: {stats.get('benign_count', 0):,}")
    logger.info(f"  Malicious: {stats.get('malicious_count', 0):,}")
    
    # Export data
    output_file = Path(args.output)
    logger.info(f"Exporting to: {output_file}")
    
    export_stats = export_samples(
        data_collector, output_file,
        label=args.label, batch_size=args.batch_size
    )
    
    logger.info("="*60)
    logger.info("Export Summary")
    logger.info("="*60)
    logger.info(f"Exported: {export_stats['exported']:,} samples")
    logger.info(f"Skipped: {export_stats['skipped']:,} samples")
    logger.info(f"Errors: {export_stats['errors']:,} samples")
    logger.info(f"Output file: {output_file}")
    logger.info("="*60)
    
    if export_stats['exported'] > 0:
        logger.info("✓ Export completed successfully!")
        logger.info(f"\nYou can now upload {output_file} to Google Drive or use it in Colab.")
    else:
        logger.error("✗ Export failed - no samples exported")
        sys.exit(1)


if __name__ == '__main__':
    main()
