#!/usr/bin/env python3
"""
Create a balanced subset of CICIDS2018 dataset for hackathon training
Selects 50K-100K samples maintaining class distribution
"""

import os
import sys
import argparse
import random
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("Error: pandas and numpy are required. Install with: pip install pandas numpy")
    sys.exit(1)

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def determine_label(label_value) -> str:
    """Map CICIDS2018 label to benign/malicious"""
    if pd.isna(label_value):
        return 'benign'
    
    label_str = str(label_value).upper().strip()
    
    # Skip header rows
    if label_str == 'LABEL' or label_str == 'LABEL ':
        return None
    
    # Benign
    if 'BENIGN' in label_str:
        return 'benign'
    
    # Malicious patterns
    malicious_patterns = [
        'BRUTE', 'BRUTE-FORCE', 'BRUTEFORCE',
        'DDOS', 'DOS', 'DOS ATTACKS', 'DDOS ATTACK',
        'INFILTERATION', 'INFILTRATION',
        'BOT',
        'SQL', 'XSS',
        'ATTACK'
    ]
    
    for pattern in malicious_patterns:
        if pattern in label_str:
            return 'malicious'
    
    # Default to benign if unclear
    return 'benign'


def load_and_categorize_csv(csv_path: Path, chunk_size: int = 50000) -> Tuple[List[pd.DataFrame], List[pd.DataFrame]]:
    """Load CSV file and categorize rows into benign and malicious"""
    benign_rows = []
    malicious_rows = []
    
    logger.info(f"Loading {csv_path.name}...")
    
    try:
        # Find label column
        first_chunk = pd.read_csv(csv_path, nrows=100, low_memory=False)
        label_col = None
        for col in ['Label', 'label', 'Label ', 'label ']:
            if col in first_chunk.columns:
                label_col = col
                break
        
        if not label_col:
            logger.warning(f"No label column found in {csv_path.name}, skipping")
            return benign_rows, malicious_rows
        
        # Read file in chunks
        chunk_iter = pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False)
        
        if TQDM_AVAILABLE:
            # Count total chunks first (approximate)
            total_rows = sum(1 for _ in open(csv_path)) - 1
            total_chunks = (total_rows // chunk_size) + 1
            chunk_iter = tqdm(chunk_iter, desc=f"  Processing {csv_path.name}", 
                            total=total_chunks, unit="chunk")
        
        for chunk in chunk_iter:
            # Skip header rows
            chunk = chunk[chunk[label_col].astype(str).str.upper() != 'LABEL']
            chunk = chunk[chunk[label_col].astype(str).str.upper() != 'LABEL ']
            
            # Categorize rows
            for idx, row in chunk.iterrows():
                label = determine_label(row[label_col])
                
                if label is None:
                    continue
                elif label == 'benign':
                    benign_rows.append(row.to_frame().T)
                else:
                    malicious_rows.append(row.to_frame().T)
    
    except Exception as e:
        logger.error(f"Error loading {csv_path.name}: {e}")
        import traceback
        traceback.print_exc()
    
    return benign_rows, malicious_rows


def create_balanced_subset(input_dir: Path, output_file: Path, 
                           total_samples: int, benign_ratio: float = 0.6,
                           chunk_size: int = 50000) -> bool:
    """Create balanced subset from CICIDS2018 CSV files"""
    
    logger.info("="*60)
    logger.info("Creating Training Subset")
    logger.info("="*60)
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Total samples: {total_samples:,}")
    logger.info(f"Benign ratio: {benign_ratio:.1%}")
    logger.info("="*60)
    
    # Find all CSV files
    csv_files = list(input_dir.glob("*.csv"))
    
    if not csv_files:
        logger.error(f"No CSV files found in {input_dir}")
        return False
    
    logger.info(f"Found {len(csv_files)} CSV files")
    
    # Load and categorize data efficiently (process one file at a time, sample immediately)
    logger.info("\nLoading and sampling dataset files...")
    all_benign_samples = []
    all_malicious_samples = []
    
    target_benign = int(total_samples * benign_ratio)
    target_malicious = total_samples - target_benign
    
    # Track counts to know when we have enough
    benign_count = 0
    malicious_count = 0
    
    for csv_file in csv_files:
        if benign_count >= target_benign and malicious_count >= target_malicious:
            logger.info(f"  Sufficient samples collected, skipping remaining files")
            break
            
        logger.info(f"  Processing {csv_file.name}...")
        benign_rows, malicious_rows = load_and_categorize_csv(csv_file, chunk_size)
        
        # Add samples if we need more
        if benign_count < target_benign:
            needed_benign = target_benign - benign_count
            samples_to_add = min(needed_benign, len(benign_rows))
            if samples_to_add > 0:
                # Randomly sample from this file's benign rows
                random.seed(42)
                sampled = random.sample(benign_rows, samples_to_add) if len(benign_rows) > samples_to_add else benign_rows
                all_benign_samples.extend(sampled)
                benign_count += len(sampled)
        
        if malicious_count < target_malicious:
            needed_malicious = target_malicious - malicious_count
            samples_to_add = min(needed_malicious, len(malicious_rows))
            if samples_to_add > 0:
                # Randomly sample from this file's malicious rows
                random.seed(42)
                sampled = random.sample(malicious_rows, samples_to_add) if len(malicious_rows) > samples_to_add else malicious_rows
                all_malicious_samples.extend(sampled)
                malicious_count += len(sampled)
        
        logger.info(f"    Collected: {benign_count:,} benign, {malicious_count:,} malicious so far")
        
        # Clear memory
        del benign_rows, malicious_rows
    
    # Convert to DataFrames
    logger.info("\nCombining sampled data...")
    if all_benign_samples:
        benign_df = pd.concat(all_benign_samples, ignore_index=True)
        del all_benign_samples
    else:
        logger.error("No benign samples found!")
        return False
    
    if all_malicious_samples:
        malicious_df = pd.concat(all_malicious_samples, ignore_index=True)
        del all_malicious_samples
    else:
        logger.error("No malicious samples found!")
        return False
    
    total_benign = len(benign_df)
    total_malicious = len(malicious_df)
    
    logger.info(f"\nCollected Samples:")
    logger.info(f"  Benign: {total_benign:,}")
    logger.info(f"  Malicious: {total_malicious:,}")
    
    # Use what we have (already sampled to target)
    target_benign = min(total_benign, int(total_samples * benign_ratio))
    target_malicious = min(total_malicious, total_samples - target_benign)
    
    # Final sampling if we collected more than needed
    logger.info(f"\nCreating final balanced subset...")
    logger.info(f"  Target: {target_benign:,} benign, {target_malicious:,} malicious")
    
    if len(benign_df) > target_benign:
        benign_subset = benign_df.sample(n=target_benign, random_state=42, replace=False)
    else:
        benign_subset = benign_df
    
    if len(malicious_df) > target_malicious:
        malicious_subset = malicious_df.sample(n=target_malicious, random_state=42, replace=False)
    else:
        malicious_subset = malicious_df
    
    del benign_df, malicious_df  # Free memory
    
    # Combine and shuffle
    logger.info("Combining and shuffling...")
    subset_df = pd.concat([benign_subset, malicious_subset], ignore_index=True)
    subset_df = subset_df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Verify label distribution
    label_col = None
    for col in ['Label', 'label', 'Label ', 'label ']:
        if col in subset_df.columns:
            label_col = col
            break
    
    if label_col:
        label_counts = subset_df[label_col].value_counts()
        logger.info(f"\nSubset Label Distribution:")
        for label, count in label_counts.items():
            pct = (count / len(subset_df)) * 100
            label_type = determine_label(label)
            logger.info(f"  {label}: {count:,} ({pct:.1f}%) - {label_type}")
    
    # Save to CSV
    logger.info(f"\nSaving subset to: {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        subset_df.to_csv(output_file, index=False)
        file_size = output_file.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"Subset saved successfully!")
        logger.info(f"  File size: {file_size:.2f} MB")
        logger.info(f"  Total samples: {len(subset_df):,}")
        logger.info("="*60)
        return True
    except Exception as e:
        logger.error(f"Error saving subset: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Create balanced subset of CICIDS2018 dataset for training'
    )
    parser.add_argument(
        '--input-dir',
        type=str,
        default='./data/cicids2018',
        help='Directory containing CICIDS2018 CSV files (default: ./data/cicids2018)'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        default='./data/cicids2018_subset.csv',
        help='Output CSV file path (default: ./data/cicids2018_subset.csv)'
    )
    parser.add_argument(
        '--total-samples',
        type=int,
        default=50000,
        help='Total number of samples to select (default: 50000)'
    )
    parser.add_argument(
        '--benign-ratio',
        type=float,
        default=0.6,
        help='Ratio of benign samples (default: 0.6 = 60%%)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=50000,
        help='Chunk size for reading CSV files (default: 50000)'
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_file = Path(args.output_file)
    
    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    if not (0 < args.benign_ratio < 1):
        logger.error("Benign ratio must be between 0 and 1")
        sys.exit(1)
    
    if args.total_samples < 1000:
        logger.warning("Total samples is very small. Recommended: 50,000-100,000")
    
    success = create_balanced_subset(
        input_dir=input_dir,
        output_file=output_file,
        total_samples=args.total_samples,
        benign_ratio=args.benign_ratio,
        chunk_size=args.chunk_size
    )
    
    if success:
        logger.info("\n✓ Subset creation completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n✗ Subset creation failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
