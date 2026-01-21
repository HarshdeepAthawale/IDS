#!/usr/bin/env python3
"""
Download CICIDS2018 CSV files from AWS S3 bucket
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("Warning: boto3 not available, will try requests fallback")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Warning: tqdm not available, progress bars disabled")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# S3 Configuration
S3_BUCKET = 'cse-cic-ids2018'
S3_REGION = 'ca-central-1'
S3_PREFIX = 'Processed Traffic Data for ML Algorithms/'

# Expected CSV files (actual names in S3 bucket)
# Files are named like: Friday-02-03-2018_TrafficForML_CICFlowMeter.csv
# We'll discover files dynamically from S3 instead of hardcoding
EXPECTED_FILES = []  # Will be populated from S3 listing


def check_disk_space(output_dir: Path, required_gb: float = 7.0, strict: bool = False) -> Tuple[bool, float]:
    """
    Check if sufficient disk space is available
    
    Returns:
        Tuple of (has_space, free_gb)
    """
    try:
        stat = shutil.disk_usage(output_dir)
        free_gb = stat.free / (1024 ** 3)
        if free_gb < required_gb:
            if strict:
                print(f"Error: Only {free_gb:.2f} GB free, need at least {required_gb} GB")
                return False, free_gb
            else:
                print(f"Warning: Only {free_gb:.2f} GB free, need at least {required_gb} GB")
                print(f"Will attempt to download files that fit. Some files may be skipped.")
                return True, free_gb  # Allow partial downloads
        return True, free_gb
    except Exception as e:
        print(f"Warning: Could not check disk space: {e}")
        return True, 0.0  # Continue anyway


def get_file_list_boto3() -> List[str]:
    """List CSV files in S3 bucket using boto3"""
    if not BOTO3_AVAILABLE:
        return []
    
    try:
        s3_client = boto3.client(
            's3',
            region_name=S3_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        
        files = []
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith('.csv') and 'TrafficForML_CICFlowMeter' in key:
                        filename = os.path.basename(key)
                        files.append(filename)
        
        return sorted(files)
    except Exception as e:
        print(f"Error listing S3 files: {e}")
        return []


def download_file_boto3(s3_key: str, local_path: Path, show_progress: bool = True) -> bool:
    """Download a file from S3 using boto3"""
    if not BOTO3_AVAILABLE:
        return False
    
    try:
        s3_client = boto3.client(
            's3',
            region_name=S3_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        
        # Get file size for progress bar
        response = s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        file_size = response['ContentLength']
        
        # Download with progress
        if show_progress and TQDM_AVAILABLE:
            with tqdm(total=file_size, unit='B', unit_scale=True, desc=os.path.basename(local_path)) as pbar:
                s3_client.download_fileobj(
                    S3_BUCKET,
                    s3_key,
                    open(local_path, 'wb'),
                    Callback=lambda bytes_transferred: pbar.update(bytes_transferred)
                )
        else:
            s3_client.download_file(S3_BUCKET, s3_key, str(local_path))
        
        return True
    except Exception as e:
        print(f"Error downloading {s3_key}: {e}")
        return False


def download_file_requests(s3_key: str, local_path: Path, show_progress: bool = True) -> bool:
    """Download a file from S3 using requests (fallback)"""
    if not REQUESTS_AVAILABLE:
        return False
    
    try:
        url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        file_size = int(response.headers.get('content-length', 0))
        
        with open(local_path, 'wb') as f:
            if show_progress and TQDM_AVAILABLE and file_size > 0:
                with tqdm(total=file_size, unit='B', unit_scale=True, desc=os.path.basename(local_path)) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            else:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        
        return True
    except Exception as e:
        print(f"Error downloading {s3_key}: {e}")
        return False


def validate_csv_file(csv_path: Path) -> bool:
    """Validate CSV file structure"""
    if not PANDAS_AVAILABLE:
        # Basic check: file exists and is readable
        return csv_path.exists() and csv_path.stat().st_size > 0
    
    try:
        # Read first few rows to check structure
        df = pd.read_csv(csv_path, nrows=5, low_memory=False)
        
        # Check for required columns
        required_cols = ['Flow Duration', 'Protocol', 'Label']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Warning: Missing columns in {csv_path.name}: {missing_cols}")
            # Try alternative column names
            alt_cols = {
                'Flow Duration': ['FlowDuration', 'flow_duration'],
                'Protocol': ['protocol'],
                'Label': ['label', 'Label']
            }
            for req_col, alternatives in alt_cols.items():
                if req_col not in df.columns:
                    found = False
                    for alt in alternatives:
                        if alt in df.columns:
                            found = True
                            break
                    if not found:
                        print(f"Error: Required column '{req_col}' not found")
                        return False
        
        # Check file has data
        if len(df) == 0:
            print(f"Warning: {csv_path.name} appears to be empty")
            return False
        
        return True
    except Exception as e:
        print(f"Error validating {csv_path.name}: {e}")
        return False


def get_file_size_boto3(s3_key: str) -> Optional[int]:
    """Get file size from S3 using boto3"""
    if not BOTO3_AVAILABLE:
        return None
    
    try:
        s3_client = boto3.client(
            's3',
            region_name=S3_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        response = s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return response['ContentLength']
    except Exception as e:
        print(f"Warning: Could not get file size for {s3_key}: {e}")
        return None


def get_file_size_requests(s3_key: str) -> Optional[int]:
    """Get file size from S3 using requests"""
    if not REQUESTS_AVAILABLE:
        return None
    
    try:
        url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        response = requests.head(url, timeout=10)
        if response.status_code == 200:
            return int(response.headers.get('content-length', 0))
    except Exception as e:
        print(f"Warning: Could not get file size for {s3_key}: {e}")
        return None


def download_dataset(output_dir: Path, files: Optional[List[str]] = None,
                    resume: bool = True, validate: bool = True,
                    min_space_gb: float = 7.0, allow_partial: bool = True,
                    force: bool = False) -> int:
    """Download CICIDS2018 CSV files"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check disk space (non-strict if allow_partial or force)
    has_space, free_gb = check_disk_space(output_dir, min_space_gb, strict=not (allow_partial or force))
    if not has_space and not force:
        print("Insufficient disk space. Exiting.")
        print("Use --force to bypass space check (use with caution).")
        return 0
    
    if free_gb < min_space_gb:
        if force:
            print(f"\n⚠ Low disk space detected ({free_gb:.2f} GB free)")
            print("⚠ Force mode enabled - proceeding despite low space.\n")
        else:
            print(f"\n⚠ Low disk space detected ({free_gb:.2f} GB free)")
            print("Will attempt to download files that fit. Large files may be skipped.\n")
    
    # Determine download method
    use_boto3 = BOTO3_AVAILABLE
    if not use_boto3 and not REQUESTS_AVAILABLE:
        print("\n" + "="*60)
        print("ERROR: Missing required dependencies")
        print("="*60)
        print("Neither boto3 nor requests are installed.")
        print("\nTo fix this, install the required dependencies:")
        print("  pip install -r requirements.txt")
        print("\nOr install individually:")
        print("  pip install boto3 requests")
        print("\nNote: It's recommended to use a virtual environment:")
        print("  python -m venv venv")
        print("  source venv/bin/activate  # On Linux/Mac")
        print("  # or: venv\\Scripts\\activate  # On Windows")
        print("  pip install -r requirements.txt")
        print("="*60)
        return 0
    
    # Get file list from S3 (discover actual files)
    if not EXPECTED_FILES:
        print("Discovering CSV files from S3 bucket...")
        if use_boto3:
            discovered_files = get_file_list_boto3()
        else:
            discovered_files = []  # Can't list without boto3
        
        if discovered_files:
            EXPECTED_FILES.extend(discovered_files)
            print(f"Found {len(discovered_files)} CSV files in S3 bucket")
        else:
            print("Warning: Could not discover files from S3. Using fallback list.")
            # Fallback to some common file patterns
            EXPECTED_FILES.extend([
                'Friday-02-03-2018_TrafficForML_CICFlowMeter.csv',
                'Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv',
                'Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv',
                'Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv',
            ])
    
    # Get file list
    if files is None:
        files_to_download = EXPECTED_FILES
    else:
        files_to_download = [f for f in EXPECTED_FILES if any(day.lower() in f.lower() for day in files)]
    
    if not files_to_download:
        print("No files to download")
        return 0
    
    downloaded_count = 0
    skipped_count = 0
    
    print(f"Downloading {len(files_to_download)} CSV files to {output_dir}")
    
    for filename in files_to_download:
        local_path = output_dir / filename
        s3_key = S3_PREFIX + filename
        
        # Skip if file exists and resume is enabled
        if resume and local_path.exists():
            print(f"Skipping {filename} (already exists)")
            if validate:
                if validate_csv_file(local_path):
                    downloaded_count += 1
                    continue
                else:
                    print(f"Existing file {filename} is invalid, re-downloading...")
                    local_path.unlink()
            else:
                downloaded_count += 1
                continue
        
        # Check file size before downloading if we have low space (unless forced)
        if not force and free_gb < min_space_gb:
            file_size_bytes = None
            if use_boto3:
                file_size_bytes = get_file_size_boto3(s3_key)
            else:
                file_size_bytes = get_file_size_requests(s3_key)
            
            if file_size_bytes:
                file_size_gb = file_size_bytes / (1024 ** 3)
                # Reserve 0.5 GB buffer for other operations
                if file_size_gb > (free_gb - 0.5):
                    print(f"Skipping {filename} ({file_size_gb:.2f} GB) - insufficient space")
                    skipped_count += 1
                    continue
        
        print(f"Downloading {filename}...")
        
        # Download file
        if use_boto3:
            success = download_file_boto3(s3_key, local_path)
        else:
            success = download_file_requests(s3_key, local_path)
        
        if success:
            # Validate if requested
            if validate:
                if validate_csv_file(local_path):
                    print(f"✓ Downloaded and validated {filename}")
                    downloaded_count += 1
                else:
                    print(f"✗ Downloaded {filename} but validation failed")
                    local_path.unlink()
            else:
                print(f"✓ Downloaded {filename}")
                downloaded_count += 1
        else:
            print(f"✗ Failed to download {filename}")
    
    print(f"\nDownloaded {downloaded_count}/{len(files_to_download)} files")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} files due to insufficient space")
    return downloaded_count


def main():
    parser = argparse.ArgumentParser(description='Download CICIDS2018 CSV files from AWS S3')
    parser.add_argument('--output-dir', type=str, default='./data/cicids2018',
                       help='Directory to save CSV files')
    parser.add_argument('--days', nargs='+', type=str,
                       help='Specific days to download (e.g., Monday Tuesday)')
    parser.add_argument('--resume', action='store_true', default=True,
                       help='Resume interrupted downloads (skip existing files)')
    parser.add_argument('--no-resume', dest='resume', action='store_false',
                       help='Re-download existing files')
    parser.add_argument('--validate', action='store_true', default=True,
                       help='Validate downloaded CSV files')
    parser.add_argument('--no-validate', dest='validate', action='store_false',
                       help='Skip CSV validation')
    parser.add_argument('--min-space', type=float, default=7.0,
                       help='Minimum required disk space in GB (default: 7.0)')
    parser.add_argument('--allow-partial', action='store_true', default=True,
                       help='Allow partial downloads if space is limited (default: True)')
    parser.add_argument('--strict-space', dest='allow_partial', action='store_false',
                       help='Require full space before starting download')
    parser.add_argument('--force', action='store_true', default=False,
                       help='Force download even if disk space is insufficient (use with caution)')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir).resolve()
    
    files = None
    if args.days:
        files = args.days
    
    downloaded = download_dataset(
        output_dir, 
        files, 
        args.resume, 
        args.validate,
        min_space_gb=args.min_space,
        allow_partial=args.allow_partial,
        force=args.force
    )
    
    if downloaded > 0:
        print(f"\n✓ Successfully downloaded {downloaded} files to {output_dir}")
        sys.exit(0)
    else:
        print("\n✗ No files were downloaded")
        sys.exit(1)


if __name__ == '__main__':
    main()
