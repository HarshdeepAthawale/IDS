#!/usr/bin/env python3
"""
Complete pipeline script for CICIDS2018 preprocessing, import, and training
Orchestrates all phases with status checking and error handling
"""

import sys
import argparse
import subprocess
from pathlib import Path
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_preprocessing_status(json_file: Path) -> dict:
    """Check if preprocessing is complete"""
    status = {
        'complete': False,
        'file_exists': False,
        'file_size_gb': 0,
        'sample_count': 0,
        'valid': False
    }
    
    if json_file.exists():
        status['file_exists'] = True
        status['file_size_gb'] = json_file.stat().st_size / (1024**3)
        
        # Try to validate JSON
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            if isinstance(data, list):
                status['sample_count'] = len(data)
                status['valid'] = True
                # Consider complete if we have close to expected count (8M+)
                if status['sample_count'] >= 7_000_000:
                    status['complete'] = True
        except Exception as e:
            logger.warning(f"Could not validate JSON: {e}")
    
    return status


def check_mongodb_status(config) -> dict:
    """Check MongoDB import status"""
    status = {
        'connected': False,
        'sample_count': 0,
        'benign_count': 0,
        'malicious_count': 0,
        'ready_for_training': False
    }
    
    try:
        from services.data_collector import DataCollector
        collector = DataCollector(config)
        stats = collector.get_statistics()
        
        status['connected'] = True
        status['sample_count'] = stats.get('total_samples', 0)
        status['benign_count'] = stats.get('benign_count', 0)
        status['malicious_count'] = stats.get('malicious_count', 0)
        
        # Ready if we have at least 1000 samples and both classes
        if status['sample_count'] >= 1000 and \
           status['benign_count'] > 0 and \
           status['malicious_count'] > 0:
            status['ready_for_training'] = True
            
    except Exception as e:
        logger.warning(f"MongoDB check failed: {e}")
    
    return status


def check_model_status(model_file: Path) -> dict:
    """Check if model is trained"""
    status = {
        'exists': False,
        'trained': False,
        'model_type': None
    }
    
    if model_file.exists():
        status['exists'] = True
        try:
            import pickle
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
            status['trained'] = model_data.get('is_trained', False)
            status['model_type'] = model_data.get('model_type', 'unknown')
        except Exception as e:
            logger.warning(f"Could not read model file: {e}")
    
    return status


def run_preprocessing(input_dir: Path, output_file: Path, chunk_size: int = 10000, 
                     resume: bool = True, validate: bool = True) -> bool:
    """Run preprocessing phase"""
    logger.info("="*60)
    logger.info("Phase 1: Preprocessing")
    logger.info("="*60)
    
    script_path = Path(__file__).parent / 'preprocess_cicids2018.py'
    
    cmd = [
        sys.executable,
        str(script_path),
        '--input-dir', str(input_dir),
        '--output-file', str(output_file),
        '--chunk-size', str(chunk_size)
    ]
    
    if resume:
        cmd.append('--resume')
    if validate:
        cmd.append('--validate')
    
    try:
        result = subprocess.run(cmd, check=True)
        logger.info("✓ Preprocessing completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Preprocessing failed: {e}")
        return False


def run_validation(json_file: Path) -> bool:
    """Run validation phase"""
    logger.info("="*60)
    logger.info("Phase 2: Validation")
    logger.info("="*60)
    
    script_path = Path(__file__).parent / 'validate_preprocessed.py'
    
    cmd = [
        sys.executable,
        str(script_path),
        '--input-file', str(json_file)
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        logger.info("✓ Validation completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Validation failed: {e}")
        return False


def run_import(json_file: Path, batch_size: int = 1000, labeled_by: str = 'cicids2018') -> bool:
    """Run MongoDB import phase"""
    logger.info("="*60)
    logger.info("Phase 3: MongoDB Import")
    logger.info("="*60)
    
    script_path = Path(__file__).parent / 'import_cicids2018.py'
    
    cmd = [
        sys.executable,
        str(script_path),
        '--input-file', str(json_file),
        '--batch-size', str(batch_size),
        '--labeled-by', labeled_by
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        logger.info("✓ Import completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def run_training(hyperparameter_tuning: bool = False) -> bool:
    """Run model training phase"""
    logger.info("="*60)
    logger.info("Phase 4: Model Training")
    logger.info("="*60)
    
    script_path = Path(__file__).parent / 'train_from_cicids2018.py'
    
    cmd = [sys.executable, str(script_path)]
    
    if hyperparameter_tuning:
        cmd.append('--hyperparameter-tuning')
    
    try:
        result = subprocess.run(cmd, check=True)
        logger.info("✓ Training completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Training failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Complete CICIDS2018 pipeline: Preprocess → Import → Train'
    )
    parser.add_argument('--input-dir', type=str, default='./data/cicids2018',
                       help='Directory with CSV files')
    parser.add_argument('--output-file', type=str, 
                       default='./data/cicids2018_preprocessed.json',
                       help='Output JSON file')
    parser.add_argument('--chunk-size', type=int, default=10000,
                       help='CSV reading chunk size')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='MongoDB import batch size')
    parser.add_argument('--skip-preprocess', action='store_true',
                       help='Skip preprocessing (assume JSON exists)')
    parser.add_argument('--skip-import', action='store_true',
                       help='Skip import (assume MongoDB populated)')
    parser.add_argument('--skip-training', action='store_true',
                       help='Skip training')
    parser.add_argument('--hyperparameter-tuning', action='store_true',
                       help='Enable hyperparameter tuning')
    parser.add_argument('--status-only', action='store_true',
                       help='Only check status, do not run pipeline')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_file = Path(args.output_file)
    model_file = Path('models/classification_model.pkl')
    
    # Load config for MongoDB checks
    try:
        from config import Config
        config = Config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)
    
    # Check current status
    logger.info("Checking current pipeline status...")
    preprocess_status = check_preprocessing_status(output_file)
    mongodb_status = check_mongodb_status(config)
    model_status = check_model_status(model_file)
    
    print("\n" + "="*60)
    print("Pipeline Status")
    print("="*60)
    print(f"Preprocessing: {'✓ Complete' if preprocess_status['complete'] else '✗ Incomplete'}")
    if preprocess_status['file_exists']:
        print(f"  File size: {preprocess_status['file_size_gb']:.2f} GB")
        print(f"  Samples: {preprocess_status['sample_count']:,}")
    print(f"\nMongoDB Import: {'✓ Complete' if mongodb_status['ready_for_training'] else '✗ Incomplete'}")
    if mongodb_status['connected']:
        print(f"  Samples: {mongodb_status['sample_count']:,}")
        print(f"  Benign: {mongodb_status['benign_count']:,}")
        print(f"  Malicious: {mongodb_status['malicious_count']:,}")
    print(f"\nModel Training: {'✓ Complete' if model_status['trained'] else '✗ Not trained'}")
    if model_status['exists']:
        print(f"  Model type: {model_status['model_type']}")
    print("="*60 + "\n")
    
    if args.status_only:
        sys.exit(0)
    
    # Run phases as needed
    success = True
    
    # Phase 1: Preprocessing
    if not args.skip_preprocess and not preprocess_status['complete']:
        if preprocess_status['file_exists']:
            logger.info("Incomplete preprocessing detected. Resuming...")
        success = run_preprocessing(input_dir, output_file, args.chunk_size, resume=True)
        if not success:
            logger.error("Pipeline stopped at preprocessing phase")
            sys.exit(1)
        
        # Validate after preprocessing
        if not run_validation(output_file):
            logger.warning("Validation had issues, but continuing...")
    else:
        logger.info("Skipping preprocessing (already complete or --skip-preprocess)")
    
    # Phase 2: Validation (if preprocessing was just run)
    if not args.skip_preprocess and success:
        if not preprocess_status['valid']:
            if not run_validation(output_file):
                logger.warning("Validation failed, but continuing...")
    
    # Phase 3: MongoDB Import
    if not args.skip_import and not mongodb_status['ready_for_training']:
        success = run_import(output_file, args.batch_size)
        if not success:
            logger.error("Pipeline stopped at import phase")
            sys.exit(1)
    else:
        logger.info("Skipping import (already complete or --skip-import)")
    
    # Phase 4: Model Training
    if not args.skip_training and not model_status['trained']:
        if not mongodb_status['ready_for_training']:
            logger.error("MongoDB not ready for training. Run import first.")
            sys.exit(1)
        
        success = run_training(args.hyperparameter_tuning)
        if not success:
            logger.error("Pipeline stopped at training phase")
            sys.exit(1)
    else:
        logger.info("Skipping training (already complete or --skip-training)")
    
    # Final status
    logger.info("\n" + "="*60)
    logger.info("Pipeline Summary")
    logger.info("="*60)
    
    final_preprocess = check_preprocessing_status(output_file)
    final_mongodb = check_mongodb_status(config)
    final_model = check_model_status(model_file)
    
    logger.info(f"Preprocessing: {'✓' if final_preprocess['complete'] else '✗'}")
    logger.info(f"MongoDB Import: {'✓' if final_mongodb['ready_for_training'] else '✗'}")
    logger.info(f"Model Training: {'✓' if final_model['trained'] else '✗'}")
    
    if final_preprocess['complete'] and final_mongodb['ready_for_training'] and final_model['trained']:
        logger.info("\n✓ All phases completed successfully!")
        logger.info("Model is ready for production use.")
    else:
        logger.info("\n⚠ Pipeline incomplete. Check status above.")


if __name__ == '__main__':
    main()
