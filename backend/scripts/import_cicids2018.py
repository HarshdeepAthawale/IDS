#!/usr/bin/env python3
"""
Import preprocessed CICIDS2018 data into MongoDB
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
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


def clean_features(features: Dict[str, Any]) -> Dict[str, float]:
    """Clean features dictionary: convert Decimal to float, handle Infinity/NaN"""
    import math
    from decimal import Decimal
    
    cleaned = {}
    for key, value in features.items():
        try:
            # Handle Decimal type
            if isinstance(value, Decimal):
                value = float(value)
            # Handle Infinity and NaN
            elif isinstance(value, (int, float)):
                if math.isinf(value) or math.isnan(value):
                    value = 0.0  # Replace Infinity/NaN with 0
                else:
                    value = float(value)
            # Handle string representations
            elif isinstance(value, str):
                if value.lower() in ['inf', 'infinity', '+inf', '+infinity']:
                    value = 0.0
                elif value.lower() in ['-inf', '-infinity']:
                    value = 0.0
                elif value.lower() in ['nan', 'none', 'null']:
                    value = 0.0
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        value = 0.0
            else:
                value = 0.0
            
            cleaned[key] = value
        except Exception as e:
            logger.debug(f"Error cleaning feature {key}: {e}")
            cleaned[key] = 0.0
    
    return cleaned


def validate_sample(sample: Dict[str, Any]) -> bool:
    """Validate sample format matches our schema (supports 80+ features)"""
    # Check required fields
    if 'features' not in sample:
        logger.warning("Sample missing 'features' field")
        return False
    
    if 'label' not in sample:
        logger.warning("Sample missing 'label' field")
        return False
    
    # Check label value
    if sample['label'] not in ['benign', 'malicious']:
        logger.warning(f"Invalid label: {sample['label']}")
        return False
    
    # Check features exist and have reasonable count
    features = sample['features']
    if not isinstance(features, dict):
        logger.warning("Features must be a dictionary")
        return False
    
    if len(features) == 0:
        logger.warning("Sample has no features")
        return False
    
    return True


def stream_preprocessed_json(json_file: Path, skip_count: int = 0):
    """Stream preprocessed samples from JSON file (memory-efficient for large files)
    
    Args:
        json_file: Path to JSON file
        skip_count: Number of samples to skip from the beginning (for resume)
    """
    logger.info(f"Streaming preprocessed data from {json_file}...")
    
    if not json_file.exists():
        logger.error(f"JSON file not found: {json_file}")
        return
    
    # Check file size
    file_size_gb = json_file.stat().st_size / (1024**3)
    logger.info(f"JSON file size: {file_size_gb:.2f} GB")
    
    if skip_count > 0:
        logger.info(f"Resuming import: skipping first {skip_count:,} samples...")
    
    # Try using ijson for streaming (with Infinity handling)
    try:
        import ijson
        import re
        logger.info("Using ijson for streaming JSON parsing...")
        logger.warning("Note: JSON file contains Infinity values - using fallback parser")
        # ijson doesn't handle Infinity well, so fall through to manual parser
        raise ImportError("Using manual parser for Infinity handling")
    except ImportError:
        logger.info("Using manual streaming parser (handles Infinity values)...")
    
    # Manual streaming parser (handles Infinity values)
    with open(json_file, 'r', encoding='utf-8') as f:
        # Skip opening bracket
        char = f.read(1)
        if char != '[':
            logger.error("JSON file does not start with '['")
            return
        
        buffer = ""
        depth = 0
        in_string = False
        escape_next = False
        samples_yielded = 0
        
        while True:
            char = f.read(1)
            if not char:
                break
            
            if escape_next:
                buffer += char
                escape_next = False
                continue
            
            if char == '\\' and not escape_next:
                buffer += char
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                buffer += char
                continue
            
            if not in_string:
                if char == '{':
                    depth += 1
                    buffer += char
                elif char == '}':
                    depth -= 1
                    buffer += char
                    if depth == 0:
                        # Complete sample found
                        try:
                            # Replace Infinity values before parsing
                            import re
                            fixed_buffer = re.sub(r':\s*Infinity\b', ': 0', buffer.strip().rstrip(','))
                            fixed_buffer = re.sub(r':\s*\+Infinity\b', ': 0', fixed_buffer)
                            fixed_buffer = re.sub(r':\s*-Infinity\b', ': 0', fixed_buffer)
                            sample = json.loads(fixed_buffer)
                            
                            # Skip samples if resuming
                            if samples_yielded < skip_count:
                                samples_yielded += 1
                                if samples_yielded % 100000 == 0:
                                    logger.info(f"Skipped {samples_yielded:,}/{skip_count:,} samples...")
                                buffer = ""
                                # Skip comma and whitespace
                                while True:
                                    peek = f.read(1)
                                    if not peek or peek == ']':
                                        return
                                    if peek not in [' ', '\n', '\t', ',']:
                                        f.seek(f.tell() - 1)
                                        break
                                continue
                            
                            yield sample
                            samples_yielded += 1
                            buffer = ""
                            # Skip comma and whitespace
                            while True:
                                peek = f.read(1)
                                if not peek or peek == ']':
                                    return
                                if peek not in [' ', '\n', '\t', ',']:
                                    f.seek(f.tell() - 1)
                                    break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Error parsing sample: {e}")
                            buffer = ""
                            continue
                else:
                    buffer += char
            else:
                buffer += char
        
        if skip_count > 0 and samples_yielded < skip_count:
            logger.warning(f"Warning: Only found {samples_yielded:,} samples to skip, but requested {skip_count:,}")


def load_preprocessed_json(json_file: Path) -> List[Dict[str, Any]]:
    """Load preprocessed samples from JSON file (handles large files with streaming)"""
    logger.info(f"Loading preprocessed data from {json_file}...")
    
    if not json_file.exists():
        logger.error(f"JSON file not found: {json_file}")
        return []
    
    try:
        # Check file size
        file_size_gb = json_file.stat().st_size / (1024**3)
        logger.info(f"JSON file size: {file_size_gb:.2f} GB")
        
        # For very large files (>5 GB), use streaming
        if file_size_gb > 5:
            logger.info("Large file detected. Using streaming import (memory-efficient)...")
            samples = list(stream_preprocessed_json(json_file))
            logger.info(f"Loaded {len(samples):,} samples from JSON file")
            return samples
        
        # For smaller files, load normally
        logger.info("Loading JSON file into memory...")
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            samples = data
        else:
            samples = [data]
        
        logger.info(f"Loaded {len(samples):,} samples from JSON file")
        return samples
        
    except MemoryError:
        logger.warning("Memory error! Falling back to streaming import...")
        samples = list(stream_preprocessed_json(json_file))
        logger.info(f"Loaded {len(samples):,} samples using streaming")
        return samples
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON file: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading JSON file: {e}")
        import traceback
        traceback.print_exc()
        return []


def import_batch(data_collector: DataCollector, samples: List[Dict[str, Any]],
                 labeled_by: str = "import", batch_size: int = 1000) -> Dict[str, int]:
    """Import samples in batches"""
    stats = {
        'imported': 0,
        'skipped': 0,
        'errors': 0
    }
    
    total_batches = (len(samples) + batch_size - 1) // batch_size
    
    logger.info(f"Importing {len(samples):,} samples in {total_batches:,} batches...")
    
    # Try to use tqdm for progress bar if available
    try:
        from tqdm import tqdm
        batch_iter = tqdm(range(0, len(samples), batch_size), 
                          desc="Importing", unit="batch", unit_scale=True)
        TQDM_AVAILABLE = True
    except ImportError:
        batch_iter = range(0, len(samples), batch_size)
        TQDM_AVAILABLE = False
    
    for batch_idx in batch_iter:
        batch = samples[batch_idx:batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1
        
        if not TQDM_AVAILABLE and batch_num % 100 == 0:
            logger.info(f"Processing batch {batch_num:,}/{total_batches:,} "
                       f"({batch_num * batch_size:,}/{len(samples):,} samples)...")
        
        # Prepare batch for import
        prepared_samples = []
        for sample in batch:
            # Validate sample
            if not validate_sample(sample):
                stats['skipped'] += 1
                continue
            
            # Clean features (convert Decimal to float, handle Infinity)
            cleaned_features = clean_features(sample['features'])
            
            # Prepare sample for DataCollector.import_dataset
            prepared_sample = {
                'features': cleaned_features,
                'label': sample['label'],
                'confidence': sample.get('confidence', 1.0),
                'source_ip': sample.get('source_ip', 'unknown'),
                'dest_ip': sample.get('dest_ip', 'unknown'),
                'protocol': sample.get('protocol', 'unknown'),
                'dst_port': sample.get('dst_port'),
                'metadata': sample.get('metadata', {})
            }
            
            prepared_samples.append(prepared_sample)
        
        # Import batch
        try:
            imported = data_collector.import_dataset(prepared_samples, labeled_by=labeled_by)
            stats['imported'] += imported
            stats['skipped'] += len(batch) - len(prepared_samples)
        except Exception as e:
            logger.error(f"Error importing batch {batch_num}: {e}")
            stats['errors'] += len(batch)
            stats['skipped'] += len(prepared_samples)
    
    return stats


def import_streaming(data_collector: DataCollector, json_file: Path,
                    labeled_by: str = "import", batch_size: int = 1000,
                    skip_count: int = 0) -> Dict[str, int]:
    """Import samples using streaming (memory-efficient for large files)
    
    Args:
        data_collector: DataCollector instance
        json_file: Path to JSON file
        labeled_by: Label source identifier
        batch_size: Batch size for imports
        skip_count: Number of samples to skip (for resume)
    """
    stats = {
        'imported': 0,
        'skipped': 0,
        'errors': 0
    }
    
    batch = []
    batch_num = 0
    
    try:
        from tqdm import tqdm
        TQDM_AVAILABLE = True
    except ImportError:
        TQDM_AVAILABLE = False
    
    if skip_count > 0:
        logger.info(f"Streaming and importing samples (batch size: {batch_size}, skipping {skip_count:,} samples)...")
    else:
        logger.info(f"Streaming and importing samples (batch size: {batch_size})...")
    
    try:
        for sample in stream_preprocessed_json(json_file, skip_count=skip_count):
            # Validate sample
            if not validate_sample(sample):
                stats['skipped'] += 1
                continue
            
            # Clean features (convert Decimal to float, handle Infinity)
            cleaned_features = clean_features(sample['features'])
            
            # Prepare sample for DataCollector.import_dataset
            prepared_sample = {
                'features': cleaned_features,
                'label': sample['label'],
                'confidence': sample.get('confidence', 1.0),
                'source_ip': sample.get('source_ip', 'unknown'),
                'dest_ip': sample.get('dest_ip', 'unknown'),
                'protocol': sample.get('protocol', 'unknown'),
                'dst_port': sample.get('dst_port'),
                'metadata': sample.get('metadata', {})
            }
            
            batch.append(prepared_sample)
            
            # Import when batch is full
            if len(batch) >= batch_size:
                batch_num += 1
                try:
                    data_collector.import_dataset(batch, labeled_by=labeled_by)
                    stats['imported'] += len(batch)
                    if TQDM_AVAILABLE:
                        tqdm.write(f"Imported batch {batch_num} ({stats['imported']:,} samples, {stats['imported']/len(batch)/batch_num*60:.0f} samples/sec)...")
                    elif batch_num % 10 == 0:  # More frequent logging for large batches
                        logger.info(f"Imported batch {batch_num} ({stats['imported']:,} samples)...")
                except Exception as e:
                    logger.error(f"Error importing batch {batch_num}: {e}")
                    stats['errors'] += len(batch)
                batch = []
        
        # Import remaining samples
        if batch:
            batch_num += 1
            try:
                data_collector.import_dataset(batch, labeled_by=labeled_by)
                stats['imported'] += len(batch)
            except Exception as e:
                logger.error(f"Error importing final batch: {e}")
                stats['errors'] += len(batch)
        
    except Exception as e:
        logger.error(f"Error during streaming import: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info(f"Streaming import complete: {stats['imported']:,} imported, "
               f"{stats['skipped']:,} skipped, {stats['errors']:,} errors")
    return stats


def get_import_statistics(data_collector: DataCollector) -> Dict[str, Any]:
    """Get import statistics"""
    try:
        stats = data_collector.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(
        description='Import preprocessed CICIDS2018 data into MongoDB',
        epilog='''
Examples:
  # Normal import
  python scripts/import_cicids2018.py --input-file data/cicids2018_preprocessed.json --batch-size 20000 --labeled-by cicids2018
  
  # Resume import (PowerShell - use backticks for line continuation)
  python scripts/import_cicids2018.py --input-file data/cicids2018_preprocessed.json --batch-size 20000 --labeled-by cicids2018 --resume
  
  # Resume import (Bash/Linux/Mac - use backslashes for line continuation)
  python scripts/import_cicids2018.py \\
      --input-file data/cicids2018_preprocessed.json \\
      --batch-size 20000 \\
      --labeled-by cicids2018 \\
      --resume
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--input-file', type=str, required=True,
                       help='Preprocessed JSON file')
    parser.add_argument('--batch-size', type=int, default=20000,
                       help='Import batch size (default: 20000 for high-performance systems)')
    parser.add_argument('--labeled-by', type=str, default='cicids2018',
                       help='Label source identifier')
    parser.add_argument('--skip-duplicates', action='store_true',
                       help='Skip duplicate samples (not implemented yet)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume import from where it stopped (skips already imported samples)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config()
    
    # Initialize DataCollector
    try:
        data_collector = DataCollector(config)
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)
    
    # Load/stream preprocessed data
    json_file = Path(args.input_file)
    file_size_gb = json_file.stat().st_size / (1024**3) if json_file.exists() else 0
    
    # Get initial statistics
    initial_stats = get_import_statistics(data_collector)
    initial_count = initial_stats.get('total_samples', 0)
    logger.info(f"Initial database statistics: {initial_stats}")
    
    # Calculate skip count if resuming
    skip_count = 0
    if args.resume:
        skip_count = initial_count
        if skip_count > 0:
            logger.info("="*70)
            logger.info("RESUMING IMPORT")
            logger.info("="*70)
            logger.info(f"Current MongoDB count: {skip_count:,} samples")
            logger.info(f"Skipping first {skip_count:,} samples from JSON file")
            logger.info("="*70)
        else:
            logger.info("Resume requested but database is empty. Starting fresh import.")
    
    # For very large files, use streaming import directly
    if file_size_gb > 5:
        logger.info("Using streaming import for large file...")
        
        # Stream and import directly
        import_stats = import_streaming(
            data_collector,
            json_file,
            labeled_by=args.labeled_by,
            batch_size=args.batch_size,
            skip_count=skip_count
        )
    else:
        # Load normally for smaller files
        samples = load_preprocessed_json(json_file)
        
        if not samples:
            logger.error("No samples to import")
            sys.exit(1)
        
        # Skip samples if resuming
        if args.resume and skip_count > 0:
            if skip_count >= len(samples):
                logger.warning(f"All samples already imported ({skip_count:,} >= {len(samples):,})")
                logger.info("Nothing to import. Import already complete.")
                sys.exit(0)
            logger.info(f"Skipping first {skip_count:,} samples (already imported)")
            samples = samples[skip_count:]
            logger.info(f"Remaining samples to import: {len(samples):,}")
        
        # Import samples
        import_stats = import_batch(
            data_collector,
            samples,
            labeled_by=args.labeled_by,
            batch_size=args.batch_size
        )
    
    # Show final statistics
    final_stats = get_import_statistics(data_collector)
    logger.info(f"Final database statistics: {final_stats}")
    
    # Print summary
    print("\n" + "="*50)
    print("Import Summary")
    print("="*50)
    if args.resume and skip_count > 0:
        print(f"Resumed from: {skip_count:,} samples")
    total_processed = import_stats['imported'] + import_stats['skipped'] + import_stats['errors']
    print(f"Total samples processed in this session: {total_processed:,}")
    print(f"Successfully imported: {import_stats['imported']:,}")
    print(f"Skipped (invalid): {import_stats['skipped']:,}")
    print(f"Errors: {import_stats['errors']:,}")
    print(f"Total samples in database: {final_stats.get('total_samples', 0):,}")
    print(f"  - Benign: {final_stats.get('benign_count', 0):,}")
    print(f"  - Malicious: {final_stats.get('malicious_count', 0):,}")
    
    # Show progress towards target
    target_samples = 8_034_453
    final_count = final_stats.get('total_samples', 0)
    if final_count > 0:
        progress = (final_count / target_samples) * 100
        remaining = max(0, target_samples - final_count)
        print(f"\nProgress: {progress:.2f}% ({final_count:,} / {target_samples:,})")
        if remaining > 0:
            print(f"Remaining: {remaining:,} samples")
        else:
            print("✓ Import complete!")
    print("="*50)
    
    if import_stats['imported'] > 0:
        logger.info("✓ Import completed successfully")
        sys.exit(0)
    else:
        logger.error("✗ No samples were imported")
        sys.exit(1)


if __name__ == '__main__':
    main()
