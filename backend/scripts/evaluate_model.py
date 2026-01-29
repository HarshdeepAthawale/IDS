#!/usr/bin/env python3
"""
Evaluate trained classification model
Provides comprehensive evaluation metrics, confusion matrix, ROC curve, and feature importance
"""

import os
import sys
import argparse
import json
from pathlib import Path
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.data_collector import DataCollector
from services.preprocessor import DataPreprocessor
from services.classifier import get_classification_detector
from services.model_trainer import ModelTrainer
from services.model_evaluator import ModelEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def evaluate_model(model_path: str, output_dir: str = None) -> bool:
    """
    Evaluate the trained model
    
    Args:
        model_path: Path to the trained model file
        output_dir: Directory to save evaluation results (optional)
        
    Returns:
        True if evaluation successful, False otherwise
    """
    try:
        start_time = datetime.utcnow()
        
        # Load configuration
        config = Config()
        
        # Check if model file exists
        model_file = Path(model_path)
        if not model_file.exists():
            logger.error(f"Model file not found: {model_path}")
            return False
        
        logger.info("="*60)
        logger.info("Model Evaluation")
        logger.info("="*60)
        logger.info(f"Model path: {model_path}")
        logger.info("")
        
        # Initialize services
        logger.info("Initializing services...")
        data_collector = DataCollector(config)
        preprocessor = DataPreprocessor(config)
        classifier = get_classification_detector(config)
        
        # Check if model is loaded
        if not classifier.is_trained:
            logger.error("Model is not trained. Please train the model first.")
            return False
        
        logger.info("✓ Model loaded successfully")
        logger.info(f"  Model type: {classifier.model_type}")
        logger.info("")
        
        # Load training data
        logger.info("Loading test data...")
        model_trainer = ModelTrainer(config, classifier, preprocessor, data_collector)
        df, _ = model_trainer.load_training_data()
        
        logger.info(f"  Total samples: {len(df):,}")
        
        # Clean and prepare data
        logger.info("Preprocessing data...")
        df_clean = preprocessor.clean_data(df)
        df_eng = preprocessor.engineer_features(df_clean)
        
        # Split data (same split as training)
        test_size = 1.0 - getattr(config, 'TRAIN_TEST_SPLIT_RATIO', 0.7)
        val_size = 0.15
        
        logger.info("Splitting data...")
        train_df, val_df, test_df = preprocessor.split_data(
            df_eng,
            test_size=test_size,
            val_size=val_size,
            stratify=True
        )
        
        logger.info(f"  Test samples: {len(test_df):,}")
        logger.info("")
        
        # Prepare test features and labels
        X_test = preprocessor.prepare_features(test_df)
        y_test = preprocessor.prepare_labels(test_df)
        
        # Initialize evaluator
        logger.info("Running evaluation...")
        evaluator = ModelEvaluator(classifier)
        
        # Generate comprehensive report
        report = evaluator.generate_report(X_test, y_test)
        
        if 'error' in report:
            logger.error(f"Evaluation error: {report['error']}")
            return False
        
        # Display metrics
        metrics = report.get('metrics', {})
        summary = report.get('summary', {})
        
        logger.info("="*60)
        logger.info("Evaluation Results")
        logger.info("="*60)
        logger.info(f"Test Samples: {summary.get('test_samples', 0):,}")
        logger.info("")
        logger.info("Performance Metrics:")
        logger.info(f"  Accuracy:  {metrics.get('accuracy', 0):.4f} ({metrics.get('accuracy', 0)*100:.2f}%)")
        logger.info(f"  Precision: {metrics.get('precision', 0):.4f} ({metrics.get('precision', 0)*100:.2f}%)")
        logger.info(f"  Recall:    {metrics.get('recall', 0):.4f} ({metrics.get('recall', 0)*100:.2f}%)")
        logger.info(f"  F1-Score:  {metrics.get('f1_score', 0):.4f} ({metrics.get('f1_score', 0)*100:.2f}%)")
        logger.info(f"  ROC-AUC:   {metrics.get('roc_auc', 0):.4f} ({metrics.get('roc_auc', 0)*100:.2f}%)")
        logger.info(f"  PR-AUC:    {metrics.get('pr_auc', 0):.4f} ({metrics.get('pr_auc', 0)*100:.2f}%)")
        logger.info("")
        
        # Confusion matrix
        cm = metrics.get('confusion_matrix', {})
        logger.info("Confusion Matrix:")
        logger.info(f"  True Negatives:  {cm.get('true_negatives', 0):,}")
        logger.info(f"  False Positives: {cm.get('false_positives', 0):,}")
        logger.info(f"  False Negatives: {cm.get('false_negatives', 0):,}")
        logger.info(f"  True Positives:  {cm.get('true_positives', 0):,}")
        logger.info("")
        
        # Per-class metrics
        per_class = metrics.get('per_class_metrics', {})
        if per_class:
            logger.info("Per-Class Metrics:")
            for class_name, class_metrics in per_class.items():
                if isinstance(class_metrics, dict):
                    logger.info(f"  {class_name.capitalize()}:")
                    logger.info(f"    Precision: {class_metrics.get('precision', 0):.4f}")
                    logger.info(f"    Recall:    {class_metrics.get('recall', 0):.4f}")
                    logger.info(f"    F1-Score:  {class_metrics.get('f1-score', 0):.4f}")
                    logger.info(f"    Support:   {class_metrics.get('support', 0):,}")
        
        # Feature importance
        logger.info("")
        logger.info("Top 10 Feature Importance:")
        feature_importance = classifier.get_feature_importance()
        if feature_importance:
            sorted_features = sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            for feature, importance in sorted_features:
                logger.info(f"  {feature}: {importance:.4f}")
        
        # Save results if output directory specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # Save full report as JSON
            report_file = output_path / f'evaluation_report_{timestamp}.json'
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info("")
            logger.info(f"✓ Evaluation report saved: {report_file}")
            
            # Save summary as text
            summary_file = output_path / f'evaluation_summary_{timestamp}.txt'
            with open(summary_file, 'w') as f:
                f.write("Model Evaluation Summary\n")
                f.write("="*60 + "\n\n")
                f.write(f"Evaluation Date: {datetime.utcnow().isoformat()}\n")
                f.write(f"Model Path: {model_path}\n")
                f.write(f"Test Samples: {summary.get('test_samples', 0):,}\n\n")
                f.write("Performance Metrics:\n")
                f.write(f"  Accuracy:  {metrics.get('accuracy', 0):.4f} ({metrics.get('accuracy', 0)*100:.2f}%)\n")
                f.write(f"  Precision: {metrics.get('precision', 0):.4f} ({metrics.get('precision', 0)*100:.2f}%)\n")
                f.write(f"  Recall:    {metrics.get('recall', 0):.4f} ({metrics.get('recall', 0)*100:.2f}%)\n")
                f.write(f"  F1-Score:  {metrics.get('f1_score', 0):.4f} ({metrics.get('f1_score', 0)*100:.2f}%)\n")
                f.write(f"  ROC-AUC:   {metrics.get('roc_auc', 0):.4f} ({metrics.get('roc_auc', 0)*100:.2f}%)\n")
                f.write(f"  PR-AUC:    {metrics.get('pr_auc', 0):.4f} ({metrics.get('pr_auc', 0)*100:.2f}%)\n\n")
                f.write("Confusion Matrix:\n")
                f.write(f"  True Negatives:  {cm.get('true_negatives', 0):,}\n")
                f.write(f"  False Positives: {cm.get('false_positives', 0):,}\n")
                f.write(f"  False Negatives: {cm.get('false_negatives', 0):,}\n")
                f.write(f"  True Positives:  {cm.get('true_positives', 0):,}\n")
            
            logger.info(f"✓ Evaluation summary saved: {summary_file}")
        
        # Calculate evaluation time
        eval_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info("")
        logger.info("="*60)
        logger.info(f"Evaluation completed in {eval_time:.2f} seconds")
        logger.info("="*60)
        
        # Check if metrics meet targets
        accuracy = metrics.get('accuracy', 0)
        precision = metrics.get('precision', 0)
        recall = metrics.get('recall', 0)
        f1 = metrics.get('f1_score', 0)
        roc_auc = metrics.get('roc_auc', 0)
        
        target_accuracy = 0.90
        target_metrics = 0.90
        
        logger.info("")
        logger.info("Target Metrics Check:")
        logger.info(f"  Accuracy > {target_accuracy*100}%: {'✓' if accuracy >= target_accuracy else '✗'} ({accuracy*100:.2f}%)")
        logger.info(f"  Precision > {target_metrics*100}%: {'✓' if precision >= target_metrics else '✗'} ({precision*100:.2f}%)")
        logger.info(f"  Recall > {target_metrics*100}%: {'✓' if recall >= target_metrics else '✗'} ({recall*100:.2f}%)")
        logger.info(f"  F1-Score > {target_metrics*100}%: {'✓' if f1 >= target_metrics else '✗'} ({f1*100:.2f}%)")
        logger.info(f"  ROC-AUC > 0.95: {'✓' if roc_auc >= 0.95 else '✗'} ({roc_auc:.4f})")
        
        all_met = (accuracy >= target_accuracy and 
                  precision >= target_metrics and 
                  recall >= target_metrics and 
                  f1 >= target_metrics and 
                  roc_auc >= 0.95)
        
        if all_met:
            logger.info("")
            logger.info("✓ All target metrics achieved!")
        else:
            logger.info("")
            logger.warning("⚠ Some target metrics not met. Consider retraining with more data or hyperparameter tuning.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate trained classification model',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate model with default settings
  python scripts/evaluate_model.py --model-path ./classification_model.pkl
  
  # Evaluate and save results to directory
  python scripts/evaluate_model.py --model-path ./classification_model.pkl --output-dir ./evaluation_results
        """
    )
    parser.add_argument(
        '--model-path',
        type=str,
        default='./classification_model.pkl',
        help='Path to the trained model file (default: ./classification_model.pkl)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Directory to save evaluation results (optional)'
    )
    
    args = parser.parse_args()
    
    logger.info("Model Evaluation Script")
    logger.info("="*60)
    
    success = evaluate_model(
        model_path=args.model_path,
        output_dir=args.output_dir
    )
    
    if success:
        logger.info("\n✓ Model evaluation completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n✗ Model evaluation failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
