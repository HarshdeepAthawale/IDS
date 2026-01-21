#!/usr/bin/env python3
"""
Complete pipeline for downloading, preprocessing, and importing CICIDS2018 dataset
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_download(download_dir: Path, skip_download: bool = False,
                min_space: float = 7.0, allow_partial: bool = True) -> bool:
    """Run download script"""
    if skip_download:
        logger.info("Skipping download (--skip-download specified)")
        return True
    
    logger.info("="*60)
    logger.info("Phase 1: Downloading CICIDS2018 CSV files")
    logger.info("="*60)
    
    script_path = Path(__file__).parent / 'download_cicids2018.py'
    
    cmd = [
        sys.executable,
        str(script_path),
        '--output-dir', str(download_dir),
        '--resume',
        '--validate',
        '--min-space', str(min_space),
    ]
    
    if allow_partial:
        cmd.append('--allow-partial')
    else:
        cmd.append('--strict-space')
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        logger.info("✓ Download completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Download failed: {e}")
        return False


def run_preprocess(input_dir: Path, output_file: Optional[Path] = None,
                  chunk_size: int = 10000, sample_size: int = 0,
                  stream: bool = False) -> bool:
    """Run preprocessing script"""
    logger.info("="*60)
    logger.info("Phase 2: Preprocessing CSV files")
    logger.info("="*60)
    
    script_path = Path(__file__).parent / 'preprocess_cicids2018.py'
    
    cmd = [
        sys.executable,
        str(script_path),
        '--input-dir', str(input_dir),
        '--chunk-size', str(chunk_size),
        '--sample-size', str(sample_size)
    ]
    
    if output_file:
        cmd.extend(['--output-file', str(output_file)])
    
    if stream:
        cmd.append('--stream')
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        logger.info("✓ Preprocessing completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Preprocessing failed: {e}")
        return False


def run_import(input_file: Path, batch_size: int = 1000,
              labeled_by: str = 'cicids2018') -> bool:
    """Run import script"""
    logger.info("="*60)
    logger.info("Phase 3: Importing to MongoDB")
    logger.info("="*60)
    
    script_path = Path(__file__).parent / 'import_cicids2018.py'
    
    cmd = [
        sys.executable,
        str(script_path),
        '--input-file', str(input_file),
        '--batch-size', str(batch_size),
        '--labeled-by', labeled_by
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        logger.info("✓ Import completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def verify_import() -> bool:
    """Verify import by checking database statistics"""
    logger.info("="*60)
    logger.info("Phase 4: Verifying import")
    logger.info("="*60)
    
    try:
        from config import Config
        from services.data_collector import DataCollector
        
        config = Config()
        data_collector = DataCollector(config)
        stats = data_collector.get_statistics()
        
        total = stats.get('total_samples', 0)
        benign = stats.get('benign_count', 0)
        malicious = stats.get('malicious_count', 0)
        
        logger.info(f"Database statistics:")
        logger.info(f"  Total samples: {total}")
        logger.info(f"  Benign: {benign}")
        logger.info(f"  Malicious: {malicious}")
        
        if total > 0:
            logger.info("✓ Import verification passed")
            return True
        else:
            logger.warning("⚠ No samples found in database")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying import: {e}")
        return False


def run_training() -> bool:
    """Run training script"""
    logger.info("="*60)
    logger.info("Phase 5: Training model")
    logger.info("="*60)
    
    script_path = Path(__file__).parent / 'train_from_cicids2018.py'
    
    cmd = [sys.executable, str(script_path)]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        logger.info("✓ Training completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Training failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Complete pipeline for CICIDS2018 dataset processing'
    )
    parser.add_argument('--download-dir', type=str, default='./data/cicids2018',
                       help='Directory to download/save CSV files')
    parser.add_argument('--preprocess-output', type=str,
                       help='JSON file path for preprocessed data (if not streaming)')
    parser.add_argument('--stream-import', action='store_true',
                       help='Stream directly to MongoDB (skip JSON file)')
    parser.add_argument('--import-batch-size', type=int, default=1000,
                       help='Batch size for MongoDB import')
    parser.add_argument('--chunk-size', type=int, default=10000,
                       help='CSV reading chunk size')
    parser.add_argument('--sample-size', type=int, default=0,
                       help='Limit samples per CSV file (0 = all, for testing use 10000)')
    parser.add_argument('--auto-train', action='store_true',
                       help='Automatically train model after import')
    parser.add_argument('--skip-download', action='store_true',
                       help='Skip download if CSV files already exist')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from last processed file')
    parser.add_argument('--min-space', type=float, default=7.0,
                       help='Minimum required disk space in GB for download (default: 7.0)')
    parser.add_argument('--allow-partial-download', action='store_true', default=True,
                       help='Allow partial downloads if space is limited (default: True)')
    parser.add_argument('--strict-space', dest='allow_partial_download', action='store_false',
                       help='Require full space before starting download')
    
    args = parser.parse_args()
    
    download_dir = Path(args.download_dir).resolve()
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine output file
    if args.stream_import:
        output_file = None
        logger.info("Stream mode: Will stream directly to MongoDB")
    else:
        if args.preprocess_output:
            output_file = Path(args.preprocess_output)
        else:
            output_file = download_dir.parent / 'cicids2018_preprocessed.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Will save preprocessed data to: {output_file}")
    
    success = True
    
    # Phase 1: Download
    if not run_download(download_dir, args.skip_download, args.min_space, args.allow_partial_download):
        logger.error("Pipeline failed at download phase")
        sys.exit(1)
    
    # Phase 2: Preprocess
    if not run_preprocess(
        download_dir,
        output_file,
        args.chunk_size,
        args.sample_size,
        args.stream_import
    ):
        logger.error("Pipeline failed at preprocessing phase")
        sys.exit(1)
    
    # Phase 3: Import (only if not streaming)
    if not args.stream_import:
        if output_file and output_file.exists():
            if not run_import(output_file, args.import_batch_size):
                logger.error("Pipeline failed at import phase")
                sys.exit(1)
        else:
            logger.error(f"Preprocessed file not found: {output_file}")
            logger.error("Note: Streaming mode is not fully implemented. Use standard mode (without --stream-import)")
            sys.exit(1)
    else:
        logger.warning("Stream mode: Not fully implemented yet. Please use standard mode.")
        logger.info("For now, preprocessing saves to JSON file. Run import separately if needed.")
    
    # Phase 4: Verify
    if not verify_import():
        logger.warning("Import verification had issues, but continuing...")
    
    # Phase 5: Train (optional)
    if args.auto_train:
        if not run_training():
            logger.error("Pipeline failed at training phase")
            sys.exit(1)
    else:
        logger.info("Skipping training (use --auto-train to enable)")
    
    logger.info("="*60)
    logger.info("✓ Pipeline completed successfully!")
    logger.info("="*60)
    
    if not args.auto_train:
        logger.info("\nTo train the model, run:")
        logger.info(f"  python scripts/train_from_cicids2018.py")
        logger.info("Or use the frontend: Analysis page → ML Training tab")


if __name__ == '__main__':
    main()
