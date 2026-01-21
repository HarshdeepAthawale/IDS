#!/usr/bin/env python3
"""
Trigger model training after CICIDS2018 data import
"""

import os
import sys
import argparse
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Suppress MongoDB SSL errors (Python 3.14 compatibility issue)
# Must be imported BEFORE any pymongo imports
try:
    import suppress_ssl_errors
except ImportError:
    # If module doesn't exist, suppress manually
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='pymongo')
    warnings.filterwarnings('ignore', message='.*SSL.*')
    warnings.filterwarnings('ignore', message='.*TLS.*')
    logging.getLogger('pymongo').setLevel(logging.CRITICAL)
    logging.getLogger('pymongo.monitoring').setLevel(logging.CRITICAL)
    logging.getLogger('pymongo.pool').setLevel(logging.CRITICAL)

from config import Config
from services.data_collector import DataCollector
from services.preprocessor import DataPreprocessor
from services.classifier import ClassificationDetector
from services.model_trainer import ModelTrainer
from services.model_evaluator import ModelEvaluator
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_sufficient_samples(data_collector: DataCollector, min_samples: int = 1000) -> bool:
    """Check if sufficient training samples exist"""
    try:
        stats = data_collector.get_statistics()
        labeled_samples = stats.get('labeled_samples', 0)
        
        logger.info(f"Labeled samples in database: {labeled_samples}")
        logger.info(f"Minimum required: {min_samples}")
        
        if labeled_samples < min_samples:
            logger.warning(f"Insufficient samples: {labeled_samples} < {min_samples}")
            return False
        
        # Check class balance
        benign_count = stats.get('benign_count', 0)
        malicious_count = stats.get('malicious_count', 0)
        
        logger.info(f"  - Benign: {benign_count}")
        logger.info(f"  - Malicious: {malicious_count}")
        
        if benign_count == 0 or malicious_count == 0:
            logger.warning("Dataset is unbalanced: missing one class")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking samples: {e}")
        return False


def check_memory_requirements(config, data_collector):
    """Check available memory and estimate requirements"""
    try:
        import psutil
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        
        stats = data_collector.get_statistics()
        total_samples = stats.get('total_samples', 0)
        
        # Estimate memory usage: ~8 bytes per feature value
        # 81 features × 8 bytes × samples ≈ memory needed
        estimated_memory_gb = (total_samples * 81 * 8) / (1024**3)
        
        logger.info("="*60)
        logger.info("Memory Check")
        logger.info("="*60)
        logger.info(f"Available RAM: {available_memory_gb:.2f} GB")
        logger.info(f"Total RAM: {total_memory_gb:.2f} GB")
        logger.info(f"Estimated memory needed: {estimated_memory_gb:.2f} GB")
        logger.info("="*60)
        
        if estimated_memory_gb > available_memory_gb * 0.8:
            logger.warning("⚠ WARNING: Estimated memory usage exceeds 80% of available RAM")
            logger.warning("Consider enabling BATCH_LOADING_ENABLED=true in config")
            if not getattr(config, 'BATCH_LOADING_ENABLED', False):
                logger.warning("Batch loading is currently disabled. Training may fail due to memory constraints.")
        
        return available_memory_gb, estimated_memory_gb
        
    except ImportError:
        logger.warning("psutil not available. Cannot check memory. Install with: pip install psutil")
        return None, None
    except Exception as e:
        logger.warning(f"Error checking memory: {e}")
        return None, None


def estimate_training_time(total_samples, hyperparameter_tuning=False):
    """Estimate training time based on dataset size"""
    # Rough estimates: ~1000 samples per second for training
    # Hyperparameter tuning multiplies by n_iter × cv_folds
    base_time_seconds = total_samples / 1000
    
    if hyperparameter_tuning:
        # Assume 20 iterations × 3 CV folds = 60x multiplier
        estimated_time_seconds = base_time_seconds * 60
    else:
        estimated_time_seconds = base_time_seconds
    
    hours = estimated_time_seconds / 3600
    minutes = (estimated_time_seconds % 3600) / 60
    
    return hours, minutes


def train_model(hyperparameter_tuning: bool = False) -> bool:
    """Train the classification model"""
    try:
        start_time = datetime.utcnow()
        
        # Load configuration
        config = Config()
        
        # Check if classification is enabled
        if not getattr(config, 'CLASSIFICATION_ENABLED', False):
            logger.warning("Classification is not enabled in config. Set CLASSIFICATION_ENABLED=true")
            # Continue anyway for script usage
        
        # Initialize services
        logger.info("Initializing services...")
        data_collector = DataCollector(config)
        preprocessor = DataPreprocessor(config)
        classifier = ClassificationDetector(config)
        model_trainer = ModelTrainer(config, classifier, preprocessor, data_collector)
        
        # Check sufficient samples (but allow training from JSON file even if DB check fails)
        min_samples = getattr(config, 'MIN_TRAINING_SAMPLES_CLASSIFICATION', 1000)
        db_check_passed = check_sufficient_samples(data_collector, min_samples)
        if not db_check_passed:
            logger.warning("Database check failed, but will attempt to load from JSON file...")
            # Don't return False - allow training to proceed with JSON file
        
        # Check memory requirements
        available_mem, estimated_mem = check_memory_requirements(config, data_collector)
        
        # Get dataset statistics
        stats = data_collector.get_statistics()
        total_samples = stats.get('total_samples', 0)
        
        # Estimate training time
        hours, minutes = estimate_training_time(total_samples, hyperparameter_tuning)
        logger.info("="*60)
        logger.info("Training Time Estimate")
        logger.info("="*60)
        logger.info(f"Total samples: {total_samples:,}")
        logger.info(f"Estimated training time: {int(hours)}h {int(minutes)}m")
        if hyperparameter_tuning:
            logger.info("(With hyperparameter tuning)")
        logger.info("="*60)
        
        # Train model
        logger.info("="*60)
        logger.info("Starting model training...")
        logger.info("="*60)
        
        if hyperparameter_tuning:
            logger.info("Hyperparameter tuning enabled")
            logger.info(f"  - Iterations: {getattr(config, 'HYPERPARAMETER_TUNING_N_ITER', 20)}")
            logger.info(f"  - CV folds: {getattr(config, 'HYPERPARAMETER_TUNING_CV', 3)}")
        else:
            logger.info("Using default hyperparameters")
        
        training_results = model_trainer.train_model(hyperparameter_tuning=hyperparameter_tuning)
        
        # Display results
        logger.info("="*60)
        logger.info("Training Results")
        logger.info("="*60)
        logger.info(f"Model type: {training_results.get('model_type', 'unknown')}")
        logger.info(f"Training samples: {training_results.get('training_samples', 0)}")
        logger.info(f"Validation samples: {training_results.get('validation_samples', 0)}")
        logger.info(f"Training time: {training_results.get('training_time', 0):.2f} seconds")
        
        # Display test metrics from training results
        test_metrics = training_results.get('test_metrics', {})
        if test_metrics:
            logger.info("\nTest Set Metrics:")
            logger.info(f"  Accuracy: {test_metrics.get('accuracy', 0):.4f}")
            logger.info(f"  Precision: {test_metrics.get('precision', 0):.4f}")
            logger.info(f"  Recall: {test_metrics.get('recall', 0):.4f}")
            logger.info(f"  F1-Score: {test_metrics.get('f1_score', 0):.4f}")
            logger.info(f"  ROC-AUC: {test_metrics.get('roc_auc', 0):.4f}")
        
        # Display hyperparameters if tuning was performed
        if training_results.get('hyperparameters'):
            logger.info("\nBest Hyperparameters:")
            for param, value in training_results['hyperparameters'].items():
                logger.info(f"  {param}: {value}")
        
        # Calculate actual training time
        actual_time = (datetime.utcnow() - start_time).total_seconds()
        actual_hours = actual_time / 3600
        actual_minutes = (actual_time % 3600) / 60
        
        logger.info("\n" + "="*60)
        logger.info("Training Summary")
        logger.info("="*60)
        logger.info(f"Actual training time: {int(actual_hours)}h {int(actual_minutes)}m ({actual_time:.2f}s)")
        logger.info(f"Training samples: {training_results.get('training_samples', 0):,}")
        logger.info(f"Validation samples: {training_results.get('validation_samples', 0):,}")
        logger.info(f"Test samples: {training_results.get('test_samples', 0):,}")
        logger.info("="*60)
        logger.info("✓ Training completed successfully!")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during training: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Train classification model from CICIDS2018 data')
    parser.add_argument('--hyperparameter-tuning', action='store_true', default=True,
                       help='Enable hyperparameter tuning (default: True, use --no-hyperparameter-tuning to disable)')
    parser.add_argument('--no-hyperparameter-tuning', dest='hyperparameter_tuning', action='store_false',
                       help='Disable hyperparameter tuning (faster but may have lower accuracy)')
    
    args = parser.parse_args()
    
    logger.info("CICIDS2018 Model Training Script")
    logger.info("="*60)
    
    success = train_model(hyperparameter_tuning=args.hyperparameter_tuning)
    
    if success:
        logger.info("\n✓ Model training completed successfully!")
        logger.info("\nThe model is now ready to use for classification.")
        logger.info("You can view metrics in the frontend: Analysis page → Model Metrics tab")
        sys.exit(0)
    else:
        logger.error("\n✗ Model training failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
