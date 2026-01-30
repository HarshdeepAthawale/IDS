#!/usr/bin/env python3
"""
Preprocess CICIDS2018 CSV files to preserve all 80+ features for ML classification
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator, Tuple
from datetime import datetime, timezone
import time
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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('preprocessing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Protocol mapping
PROTOCOL_MAP = {
    'TCP': 1,
    'UDP': 2,
    'ICMP': 3,
    6: 1,    # TCP protocol number
    17: 2,   # UDP protocol number
    1: 3     # ICMP protocol number
}


def map_protocol(protocol_value: Any) -> int:
    """Map protocol name/number to our encoding"""
    if pd.isna(protocol_value):
        return 0
    
    # Try direct lookup
    if protocol_value in PROTOCOL_MAP:
        return PROTOCOL_MAP[protocol_value]
    
    # Try string conversion
    try:
        protocol_str = str(protocol_value).upper()
        if protocol_str in PROTOCOL_MAP:
            return PROTOCOL_MAP[protocol_str]
    except:
        pass
    
    # Try numeric conversion
    try:
        protocol_num = int(float(protocol_value))
        if protocol_num in PROTOCOL_MAP:
            return PROTOCOL_MAP[protocol_num]
    except:
        pass
    
    return 0  # Unknown protocol


def determine_label(label_value: Any) -> str:
    """Map CICIDS2018 label to benign/malicious"""
    if pd.isna(label_value):
        return 'benign'  # Default to benign if missing
    
    label_str = str(label_value).upper().strip()
    
    # Skip header rows
    if label_str == 'LABEL' or label_str == 'LABEL ':
        return None  # Signal to skip this row
    
    # Benign
    if 'BENIGN' in label_str:
        return 'benign'
    
    # Malicious patterns (check these first)
    malicious_patterns = [
        'BRUTE', 'BRUTE-FORCE', 'BRUTEFORCE',
        'DOS', 'DDOS',
        'WEB ATTACK', 'WEB-ATTACK', 'WEBATTACK',
        'INFILTRATION', 'INFILTERATION',
        'BOTNET', 'BOT',
        'PORTSCAN', 'PORT SCAN', 'PORT-SCAN',
        'SQL', 'INJECTION', 'XSS',  # SQL Injection will match 'SQL' or 'INJECTION'
        'HOIC', 'LOIC', 'HULK', 'GOLDENEYE', 'SLOWLORIS', 'SLOWHTTP',
        'FTP', 'SSH',
        'ATTACK', 'MALICIOUS', 'MALWARE'
    ]
    
    for pattern in malicious_patterns:
        if pattern in label_str:
            return 'malicious'
    
    # Default to benign if unknown
    return 'benign'


def normalize_feature_name(name: str) -> str:
    """
    Normalize feature name for MongoDB compatibility
    - Replace spaces with underscores
    - Remove special characters
    - Ensure it doesn't start with $ or contain dots
    """
    # Replace spaces with underscores
    normalized = str(name).replace(' ', '_').replace('-', '_')
    # Remove special characters except underscores
    normalized = ''.join(c if c.isalnum() or c == '_' else '_' for c in normalized)
    # Remove leading/trailing underscores
    normalized = normalized.strip('_')
    # Ensure it doesn't start with $ (MongoDB reserved)
    if normalized.startswith('$'):
        normalized = 'f_' + normalized[1:]
    # Prefix with 'f_' to ensure valid MongoDB field name
    if not normalized.startswith('f_'):
        normalized = 'f_' + normalized
    return normalized


def extract_all_features(row: pd.Series, exclude_cols: List[str] = None) -> Dict[str, Any]:
    """
    Extract all features from CICIDS2018 CSV row (preserve all 80+ features)
    
    Args:
        row: Pandas Series representing a CSV row
        exclude_cols: List of column names to exclude (e.g., 'Label', 'Flow ID')
    
    Returns:
        Dictionary with all features normalized
    """
    if exclude_cols is None:
        exclude_cols = ['Label', 'label', 'Flow ID', 'FlowID', 'flow_id']
    
    features = {}
    
    # Process all columns except excluded ones
    for col_name in row.index:
        if col_name in exclude_cols:
            continue
        
        try:
            value = row[col_name]
            
            # Handle NaN/missing values
            if pd.isna(value):
                value = 0.0  # Default to 0 for missing values
            
            # Try to convert to numeric first
            try:
                numeric_val = float(value)
                features[normalize_feature_name(col_name)] = numeric_val
            except (ValueError, TypeError):
                # If not numeric, try to encode string values
                if isinstance(value, str):
                    # Try to extract numeric value from string
                    try:
                        numeric_val = float(value)
                        features[normalize_feature_name(col_name)] = numeric_val
                    except:
                        # String value - use hash or simple encoding
                        features[normalize_feature_name(col_name)] = 0.0
                else:
                    features[normalize_feature_name(col_name)] = 0.0
        
        except Exception as e:
            logger.warning(f"Error processing feature {col_name}: {e}")
            features[normalize_feature_name(col_name)] = 0.0
    
    return features


def extract_features(row: pd.Series) -> Dict[str, Any]:
    """
    Wrapper function for backward compatibility
    Now extracts all features instead of just 6
    """
    return extract_all_features(row)


def validate_csv_structure(df: pd.DataFrame) -> bool:
    """Validate that CSV has required columns (Label is required)"""
    # Check for Label column (required for training)
    label_cols = ['Label', 'label']
    has_label = any(col in df.columns for col in label_cols)
    
    if not has_label:
        logger.error("Missing required 'Label' column")
        logger.info(f"Available columns: {list(df.columns)[:10]}...")
        return False
    
    # Log feature count
    feature_count = len([col for col in df.columns if col not in label_cols])
    logger.info(f"Found {feature_count} features in CSV (excluding Label)")
    
    return True


def process_csv_file(csv_path: Path, chunk_size: int = 10000,
                    sample_size: int = 0, show_progress: bool = True) -> Iterator[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Process CSV file and yield preprocessed samples with statistics
    
    Args:
        csv_path: Path to CSV file
        chunk_size: Pandas chunk size for reading
        sample_size: Limit samples per file (0 = all)
        show_progress: Whether to show progress bar
    
    Yields:
        Tuple of (sample dictionary, statistics dictionary)
    """
    logger.info(f"Processing {csv_path.name}...")
    
    file_stats = {
        'file_name': csv_path.name,
        'samples_processed': 0,
        'errors': 0,
        'benign_count': 0,
        'malicious_count': 0,
        'start_time': time.time()
    }
    
    try:
        # Read CSV in chunks with better error handling
        try:
            # Try with error handling for newer pandas versions
            chunk_iter = pd.read_csv(
                csv_path, 
                chunksize=chunk_size, 
                low_memory=False,
                on_bad_lines='skip'  # Skip malformed lines (pandas >= 1.3.0)
            )
        except TypeError:
            # Fallback for older pandas versions
            chunk_iter = pd.read_csv(
                csv_path, 
                chunksize=chunk_size, 
                low_memory=False,
                error_bad_lines=False,  # Skip bad lines (pandas < 1.3.0)
                warn_bad_lines=False
            )
        
        # Estimate total rows for progress bar
        total_rows = 0
        try:
            # Count rows by reading file once (quick estimate)
            with open(csv_path, 'r') as f:
                total_rows = sum(1 for _ in f) - 1  # Subtract header
        except:
            pass
        
        # Create progress bar if tqdm available and show_progress enabled
        pbar = None
        if TQDM_AVAILABLE and show_progress and total_rows > 0:
            pbar = tqdm(total=total_rows, desc=csv_path.name[:40], unit='rows', unit_scale=True)
        
        for chunk_idx, chunk in enumerate(chunk_iter):
            # Validate structure on first chunk
            if chunk_idx == 0:
                if not validate_csv_structure(chunk):
                    logger.error(f"Invalid CSV structure in {csv_path.name}")
                    if pbar:
                        pbar.close()
                    return
            
            # Process each row in chunk
            for idx, row in chunk.iterrows():
                # Apply sample size limit
                if sample_size > 0 and file_stats['samples_processed'] >= sample_size:
                    logger.info(f"Reached sample size limit ({sample_size}) for {csv_path.name}")
                    if pbar:
                        pbar.close()
                    return
                
                try:
                    # Determine label first to check if this is a header row
                    label_col = 'Label' if 'Label' in row.index else 'label'
                    label = determine_label(row.get(label_col))
                    
                    # Skip header rows (when label determination returns None)
                    if label is None:
                        if pbar:
                            pbar.update(1)
                        continue
                    
                    # Extract all features (80+ features)
                    features = extract_all_features(row)
                    
                    # Skip if no features extracted
                    if not features or len(features) == 0:
                        file_stats['errors'] += 1
                        if pbar:
                            pbar.update(1)
                        continue
                    
                    # Extract metadata fields (if available) with better error handling
                    try:
                        source_ip = str(row.get('Source IP', row.get('Src IP', row.get('Source_IP', 'unknown'))))
                        dest_ip = str(row.get('Destination IP', row.get('Dst IP', row.get('Destination_IP', 'unknown'))))
                        protocol = str(row.get('Protocol', 'unknown'))
                        
                        # Handle dst_port conversion more safely
                        dst_port_val = row.get('Destination Port', row.get('Dst Port', row.get('Destination_Port', 0)))
                        try:
                            dst_port = int(float(dst_port_val)) if pd.notna(dst_port_val) else 0
                        except (ValueError, TypeError):
                            dst_port = 0
                        
                        flow_id = str(row.get('Flow ID', row.get('FlowID', row.get('Flow_ID', ''))))
                    except Exception as e:
                        logger.debug(f"Error extracting metadata for row {idx}: {e}")
                        source_ip = 'unknown'
                        dest_ip = 'unknown'
                        protocol = 'unknown'
                        dst_port = 0
                        flow_id = ''
                    
                    # Create sample with all features
                    sample = {
                        'features': features,
                        'label': label,
                        'source_ip': source_ip,
                        'dest_ip': dest_ip,
                        'protocol': protocol,
                        'dst_port': dst_port,
                        'metadata': {
                            'source_file': csv_path.name,
                            'flow_id': flow_id,
                            'feature_count': len(features)
                        }
                    }
                    
                    # Update statistics
                    file_stats['samples_processed'] += 1
                    if label == 'benign':
                        file_stats['benign_count'] += 1
                    elif label == 'malicious':
                        file_stats['malicious_count'] += 1
                    
                    if pbar:
                        pbar.update(1)
                    
                    yield sample, file_stats
                    
                except Exception as e:
                    file_stats['errors'] += 1
                    logger.warning(f"Error processing row {idx} in {csv_path.name}: {e}")
                    if pbar:
                        pbar.update(1)
                    continue
        
        file_stats['end_time'] = time.time()
        file_stats['processing_time'] = file_stats['end_time'] - file_stats['start_time']
        
        if pbar:
            pbar.close()
        
        logger.info(f"Processed {file_stats['samples_processed']} samples from {csv_path.name} "
                   f"(Errors: {file_stats['errors']}, Time: {file_stats['processing_time']:.2f}s)")
        
    except Exception as e:
        if pbar:
            pbar.close()
        logger.error(f"Error processing {csv_path.name}: {e}")
        file_stats['error_message'] = str(e)
        raise


def load_checkpoint(checkpoint_file: Path) -> Dict[str, Any]:
    """Load checkpoint file if it exists"""
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                logger.info(f"Loaded checkpoint: {checkpoint.get('files_completed', [])}")
                return checkpoint
        except Exception as e:
            logger.warning(f"Error loading checkpoint: {e}")
    return {
        'files_completed': [],
        'total_samples': 0,
        'last_file': None
    }


def save_checkpoint(checkpoint_file: Path, checkpoint_data: Dict[str, Any]):
    """Save checkpoint file"""
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
    except Exception as e:
        logger.warning(f"Error saving checkpoint: {e}")


def process_csv_directory(input_dir: Path, chunk_size: int = 10000,
                         sample_size: int = 0,
                         files: Optional[List[str]] = None,
                         resume: bool = False,
                         checkpoint_file: Optional[Path] = None,
                         show_progress: bool = True) -> Iterator[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Process all CSV files in directory with checkpoint/resume support
    
    Yields:
        Tuple of (sample dictionary, file statistics dictionary)
    """
    csv_files = list(input_dir.glob('*.csv'))
    
    if files:
        # Filter to specific files
        csv_files = [f for f in csv_files if any(fname in f.name for fname in files)]
    
    if not csv_files:
        logger.warning(f"No CSV files found in {input_dir}")
        return
    
    # Sort files by size (smallest first) for faster initial progress
    csv_files.sort(key=lambda f: f.stat().st_size)
    
    # Load checkpoint if resuming
    checkpoint_data = None
    if resume and checkpoint_file and checkpoint_file.exists():
        checkpoint_data = load_checkpoint(checkpoint_file)
        if checkpoint_data and checkpoint_data.get('files_completed'):
            completed_files = set(checkpoint_data.get('files_completed', []))
            csv_files = [f for f in csv_files if f.name not in completed_files]
            logger.info(f"Resuming: {len(completed_files)} files already processed, {len(csv_files)} remaining")
    
    logger.info(f"Found {len(csv_files)} CSV files to process")
    
    total_stats = {
        'files_processed': 0,
        'total_samples': checkpoint_data.get('total_samples', 0) if checkpoint_data else 0,
        'total_errors': 0,
        'total_benign': checkpoint_data.get('total_benign', 0) if checkpoint_data else 0,
        'total_malicious': checkpoint_data.get('total_malicious', 0) if checkpoint_data else 0,
        'file_stats': []
    }
    
    for csv_file in csv_files:
        try:
            file_stats = None
            for sample, stats in process_csv_file(csv_file, chunk_size, sample_size, show_progress):
                file_stats = stats
                yield sample, stats
            
            # Update checkpoint after each file completes
            if file_stats:
                total_stats['files_processed'] += 1
                total_stats['total_samples'] += file_stats.get('samples_processed', 0)
                total_stats['total_errors'] += file_stats.get('errors', 0)
                total_stats['total_benign'] += file_stats.get('benign_count', 0)
                total_stats['total_malicious'] += file_stats.get('malicious_count', 0)
                total_stats['file_stats'].append(file_stats)
                
                if checkpoint_file:
                    checkpoint_data = {
                        'last_file': csv_file.name,
                        'files_completed': checkpoint_data.get('files_completed', []) + [csv_file.name] if checkpoint_data else [csv_file.name],
                        'total_samples': total_stats['total_samples'],
                        'total_benign': total_stats['total_benign'],
                        'total_malicious': total_stats['total_malicious'],
                        'last_update': datetime.now(timezone.utc).isoformat()
                    }
                    save_checkpoint(checkpoint_file, checkpoint_data)
                
        except Exception as e:
            logger.error(f"Failed to process {csv_file.name}: {e}")
            total_stats['total_errors'] += 1
            continue


def save_preprocessed(samples: Iterator[Tuple[Dict[str, Any], Dict[str, Any]]], output_file: Path, append: bool = False):
    """
    Save preprocessed samples to JSON file with statistics tracking
    
    Args:
        samples: Iterator yielding tuples of (sample, file_stats)
        output_file: Path to output JSON file
        append: If True and output_file exists, append to it instead of overwriting
    """
    logger.info(f"Saving preprocessed samples to {output_file}...")
    
    count = 0
    temp_file = output_file.with_suffix('.json.tmp')
    start_time = time.time()
    last_flush_time = start_time
    
    # Statistics tracking
    stats_summary = {
        'total_samples': 0,
        'benign_count': 0,
        'malicious_count': 0,
        'files_processed': set(),
        'errors': 0
    }
    
    # Check if we should append to existing file
    append_mode = append and output_file.exists() and output_file.stat().st_size > 0
    
    try:
        if append_mode:
            # Append mode: copy existing file and modify to append new samples
            logger.info(f"Appending to existing file: {output_file}")
            import shutil
            shutil.copy2(output_file, temp_file)
            # Remove closing bracket and add comma to append
            with open(temp_file, 'r+b') as f:
                f.seek(-10, 2)  # Go back a bit to find the closing bracket
                content = f.read()
                # Find the last ']' in the file
                last_bracket_pos = content.rfind(b']')
                if last_bracket_pos != -1:
                    # Calculate absolute position
                    abs_pos = f.tell() - len(content) + last_bracket_pos
                    f.seek(abs_pos)
                    f.truncate()
                    f.write(b',\n')
                else:
                    # If no closing bracket found, add comma at end
                    f.seek(0, 2)
                    f.write(b',\n')
            
            first = False  # Not first sample since we're appending
            file_mode = 'a'  # Append mode for writing new samples
        else:
            # New file mode
            first = True
            file_mode = 'w'
        
        with open(temp_file, file_mode) as f:
            if not append_mode:
                f.write('[\n')
            
            try:
                for sample_data in samples:
                    # Handle both old format (just sample) and new format (sample, stats)
                    if isinstance(sample_data, tuple):
                        sample, file_stats = sample_data
                        # Update statistics
                        stats_summary['files_processed'].add(sample.get('metadata', {}).get('source_file', 'unknown'))
                        if file_stats:
                            stats_summary['errors'] += file_stats.get('errors', 0)
                    else:
                        sample = sample_data
                    
                    if not first:
                        f.write(',\n')
                    json.dump(sample, f, indent=2)
                    first = False
                    count += 1
                    stats_summary['total_samples'] += 1
                    
                    if sample.get('label') == 'benign':
                        stats_summary['benign_count'] += 1
                    elif sample.get('label') == 'malicious':
                        stats_summary['malicious_count'] += 1
                    
                    # Flush every 10,000 samples or every 30 seconds
                    current_time = time.time()
                    if count % 10000 == 0 or (current_time - last_flush_time) > 30:
                        logger.info(f"Saved {count:,} samples... "
                                   f"(Benign: {stats_summary['benign_count']:,}, "
                                   f"Malicious: {stats_summary['malicious_count']:,})")
                        f.flush()
                        last_flush_time = current_time
                        
            except Exception as e:
                logger.error(f"Error saving samples: {e}")
                raise
            finally:
                # Always close the array properly, even on error
                f.write('\n]')
                f.flush()
        
        # Only rename to final file if successful
        if temp_file.exists() and count > 0:
            # Ensure file ends with closing bracket
            with open(temp_file, 'r+b') as f:
                f.seek(-1, 2)
                last_char = f.read(1)
                if last_char != b']':
                    f.write(b'\n]')
            
            temp_file.replace(output_file)
            elapsed_time = time.time() - start_time
            action = "Appended" if append_mode else "Saved"
            logger.info(f"✓ {action} {count:,} samples to {output_file}")
            logger.info(f"  Processing time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
            logger.info(f"  Samples per second: {count/elapsed_time:.2f}")
            logger.info(f"  Label distribution: Benign={stats_summary['benign_count']:,} "
                       f"({stats_summary['benign_count']/count*100:.1f}%), "
                       f"Malicious={stats_summary['malicious_count']:,} "
                       f"({stats_summary['malicious_count']/count*100:.1f}%)")
            logger.info(f"  Files processed: {len(stats_summary['files_processed'])}")
            if stats_summary['errors'] > 0:
                logger.warning(f"  Total errors encountered: {stats_summary['errors']}")
        else:
            if temp_file.exists() and not append_mode:
                temp_file.unlink()
            raise ValueError(f"No samples were saved (count: {count})")
            
    except Exception as e:
        logger.error(f"Error in save_preprocessed: {e}")
        # Clean up temp file if it exists
        if temp_file.exists():
            temp_file.unlink()
        raise


def validate_preprocessed_json(json_file: Path) -> Dict[str, Any]:
    """Validate preprocessed JSON file and return statistics"""
    logger.info(f"Validating preprocessed JSON file: {json_file}")
    
    validation_results = {
        'valid': False,
        'total_samples': 0,
        'benign_count': 0,
        'malicious_count': 0,
        'feature_count': 0,
        'files_seen': set(),
        'errors': []
    }
    
    try:
        # Try to load JSON file
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            validation_results['errors'].append("JSON file is not a list")
            return validation_results
        
        validation_results['total_samples'] = len(data)
        
        # Validate each sample
        for idx, sample in enumerate(data):
            try:
                # Check required fields
                if 'features' not in sample:
                    validation_results['errors'].append(f"Sample {idx} missing 'features'")
                    continue
                if 'label' not in sample:
                    validation_results['errors'].append(f"Sample {idx} missing 'label'")
                    continue
                
                # Count labels
                label = sample.get('label')
                if label == 'benign':
                    validation_results['benign_count'] += 1
                elif label == 'malicious':
                    validation_results['malicious_count'] += 1
                
                # Check feature count
                features = sample.get('features', {})
                if isinstance(features, dict):
                    feature_count = len(features)
                    if validation_results['feature_count'] == 0:
                        validation_results['feature_count'] = feature_count
                    elif feature_count != validation_results['feature_count']:
                        validation_results['errors'].append(
                            f"Inconsistent feature count: expected {validation_results['feature_count']}, "
                            f"got {feature_count} in sample {idx}"
                        )
                
                # Track source files
                source_file = sample.get('metadata', {}).get('source_file', 'unknown')
                validation_results['files_seen'].add(source_file)
                
            except Exception as e:
                validation_results['errors'].append(f"Error validating sample {idx}: {e}")
        
        validation_results['valid'] = len(validation_results['errors']) == 0
        
        logger.info(f"Validation complete:")
        logger.info(f"  Valid: {validation_results['valid']}")
        logger.info(f"  Total samples: {validation_results['total_samples']:,}")
        logger.info(f"  Benign: {validation_results['benign_count']:,} "
                   f"({validation_results['benign_count']/validation_results['total_samples']*100:.1f}%)")
        logger.info(f"  Malicious: {validation_results['malicious_count']:,} "
                   f"({validation_results['malicious_count']/validation_results['total_samples']*100:.1f}%)")
        logger.info(f"  Features per sample: {validation_results['feature_count']}")
        logger.info(f"  Source files: {len(validation_results['files_seen'])}")
        if validation_results['errors']:
            logger.warning(f"  Validation errors: {len(validation_results['errors'])}")
            for error in validation_results['errors'][:10]:  # Show first 10 errors
                logger.warning(f"    - {error}")
        
        return validation_results
        
    except json.JSONDecodeError as e:
        validation_results['errors'].append(f"Invalid JSON: {e}")
        logger.error(f"JSON file is invalid: {e}")
        return validation_results
    except Exception as e:
        validation_results['errors'].append(f"Error reading file: {e}")
        logger.error(f"Error validating JSON file: {e}")
        return validation_results


def main():
    parser = argparse.ArgumentParser(description='Preprocess CICIDS2018 CSV files')
    parser.add_argument('--input-dir', type=str, required=True,
                       help='Directory with CICIDS2018 CSV files')
    parser.add_argument('--output-file', type=str,
                       help='Output JSON file for preprocessed data')
    parser.add_argument('--chunk-size', type=int, default=10000,
                       help='Pandas chunk size for reading CSV')
    parser.add_argument('--sample-size', type=int, default=0,
                       help='Limit number of samples per file (0 = all)')
    parser.add_argument('--files', type=str,
                       help='Process specific CSV files only (comma-separated)')
    parser.add_argument('--stream', action='store_true',
                       help='Stream directly to MongoDB (requires import script)')
    parser.add_argument('--keep-all-features', action='store_true', default=True,
                       help='Keep all 80+ features (default: True)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from checkpoint if available')
    parser.add_argument('--checkpoint-file', type=str,
                       default='preprocessing_checkpoint.json',
                       help='Checkpoint file path (default: preprocessing_checkpoint.json)')
    parser.add_argument('--validate', action='store_true',
                       help='Validate JSON file after preprocessing')
    parser.add_argument('--no-progress', action='store_true',
                       help='Disable progress bars')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    files = None
    if args.files:
        files = [f.strip() for f in args.files.split(',')]
    
    # Setup checkpoint file path
    checkpoint_file = None
    if args.resume or args.output_file:
        checkpoint_path = Path(args.checkpoint_file)
        checkpoint_file = checkpoint_path
    
    # Check disk space if output file specified
    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check available disk space (rough estimate: need ~25 GB)
        import shutil
        free_space_gb = shutil.disk_usage(output_path.parent).free / (1024**3)
        if free_space_gb < 25:
            logger.warning(f"Low disk space: {free_space_gb:.2f} GB available. "
                          f"Recommended: at least 25 GB for 8M+ records.")
    
    # Process CSV files
    samples = process_csv_directory(
        input_dir,
        chunk_size=args.chunk_size,
        sample_size=args.sample_size,
        files=files,
        resume=args.resume,
        checkpoint_file=checkpoint_file,
        show_progress=not args.no_progress
    )
    
    # Save to JSON file if output specified
    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if args.stream:
            logger.info("Stream mode: samples will be streamed to import script")
            logger.info("Note: Currently saving to JSON file. True streaming requires integrated pipeline.")
        
        # Save samples to JSON
        try:
            # Use append mode if resuming and output file exists
            append_mode = args.resume and output_path.exists() and output_path.stat().st_size > 0
            save_preprocessed(samples, output_path, append=append_mode)
            logger.info(f"✓ Preprocessing complete. Output saved to {output_path}")
            
            # Validate JSON file if requested
            if args.validate:
                logger.info("="*60)
                logger.info("Running validation...")
                logger.info("="*60)
                validation_results = validate_preprocessed_json(output_path)
                
                if validation_results['valid']:
                    logger.info("✓ Validation passed!")
                else:
                    logger.warning("⚠ Validation found issues. Check logs above.")
                    
        except KeyboardInterrupt:
            logger.warning("Processing interrupted by user")
            if checkpoint_file:
                logger.info(f"Checkpoint saved. Resume with --resume flag.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error during preprocessing: {e}")
            if checkpoint_file:
                logger.info(f"Checkpoint saved. Resume with --resume flag.")
            raise
    else:
        # Just process and count
        count = 0
        for sample_data in samples:
            if isinstance(sample_data, tuple):
                count += 1
            else:
                count += 1
        logger.info(f"✓ Processed {count:,} samples (no output file specified)")


if __name__ == '__main__':
    main()
