"""
Model evaluation service for supervised ML classification
Provides comprehensive evaluation metrics and visualization data
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, roc_curve,
    precision_recall_curve, average_precision_score,
    classification_report
)
from services.classifier import ClassificationDetector

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    Service for evaluating classification models
    """
    
    def __init__(self, classifier: ClassificationDetector):
        """
        Initialize model evaluator
        
        Args:
            classifier: ClassificationDetector instance
        """
        self.classifier = classifier
        logger.info("ModelEvaluator initialized")
    
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        Comprehensive model evaluation
        
        Args:
            X: Test features
            y: True labels (0=benign, 1=malicious)
            
        Returns:
            Dictionary with evaluation metrics
        """
        try:
            if not self.classifier.is_trained:
                return {'error': 'Model not trained'}
            
            # Get predictions and probabilities
            predictions = self.classifier.predict(X)
            probabilities = self.classifier.predict_proba(X)
            
            # Binary classification metrics
            accuracy = accuracy_score(y, predictions)
            precision = precision_score(y, predictions, zero_division=0)
            recall = recall_score(y, predictions, zero_division=0)
            f1 = f1_score(y, predictions, zero_division=0)
            
            # Confusion matrix
            cm = confusion_matrix(y, predictions)
            tn, fp, fn, tp = cm.ravel()
            
            # Specificity (True Negative Rate)
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            
            # ROC-AUC
            try:
                roc_auc = roc_auc_score(y, probabilities[:, 1])
            except ValueError:
                roc_auc = 0.0
            
            # Precision-Recall AUC
            try:
                pr_auc = average_precision_score(y, probabilities[:, 1])
            except ValueError:
                pr_auc = 0.0
            
            # ROC curve data
            fpr, tpr, roc_thresholds = roc_curve(y, probabilities[:, 1])
            
            # Precision-Recall curve data
            precision_curve, recall_curve, pr_thresholds = precision_recall_curve(y, probabilities[:, 1])
            
            # Per-class metrics
            class_report = classification_report(y, predictions, output_dict=True, zero_division=0)
            
            metrics = {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'specificity': float(specificity),
                'roc_auc': float(roc_auc),
                'pr_auc': float(pr_auc),
                'confusion_matrix': {
                    'true_negatives': int(tn),
                    'false_positives': int(fp),
                    'false_negatives': int(fn),
                    'true_positives': int(tp),
                    'matrix': cm.tolist()
                },
                'roc_curve': {
                    'fpr': fpr.tolist(),
                    'tpr': tpr.tolist(),
                    'thresholds': roc_thresholds.tolist()
                },
                'pr_curve': {
                    'precision': precision_curve.tolist(),
                    'recall': recall_curve.tolist(),
                    'thresholds': pr_thresholds.tolist()
                },
                'per_class_metrics': {
                    'benign': class_report.get('0', {}),
                    'malicious': class_report.get('1', {})
                },
                'classification_report': class_report
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return {'error': str(e)}
    
    def get_confusion_matrix(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        Get confusion matrix
        
        Args:
            X: Test features
            y: True labels
            
        Returns:
            Dictionary with confusion matrix data
        """
        try:
            predictions = self.classifier.predict(X)
            cm = confusion_matrix(y, predictions)
            tn, fp, fn, tp = cm.ravel()
            
            return {
                'matrix': cm.tolist(),
                'true_negatives': int(tn),
                'false_positives': int(fp),
                'false_negatives': int(fn),
                'true_positives': int(tp),
                'labels': ['benign', 'malicious']
            }
            
        except Exception as e:
            logger.error(f"Error getting confusion matrix: {e}")
            return {'error': str(e)}
    
    def get_roc_curve(self, X: np.ndarray, y: np.ndarray) -> Dict[str, List[float]]:
        """
        Get ROC curve data
        
        Args:
            X: Test features
            y: True labels
            
        Returns:
            Dictionary with FPR, TPR, and thresholds
        """
        try:
            probabilities = self.classifier.predict_proba(X)
            fpr, tpr, thresholds = roc_curve(y, probabilities[:, 1])
            
            return {
                'fpr': fpr.tolist(),
                'tpr': tpr.tolist(),
                'thresholds': thresholds.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error getting ROC curve: {e}")
            return {'error': str(e)}
    
    def get_precision_recall_curve(self, X: np.ndarray, y: np.ndarray) -> Dict[str, List[float]]:
        """
        Get Precision-Recall curve data
        
        Args:
            X: Test features
            y: True labels
            
        Returns:
            Dictionary with precision, recall, and thresholds
        """
        try:
            probabilities = self.classifier.predict_proba(X)
            precision, recall, thresholds = precision_recall_curve(y, probabilities[:, 1])
            
            return {
                'precision': precision.tolist(),
                'recall': recall.tolist(),
                'thresholds': thresholds.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error getting PR curve: {e}")
            return {'error': str(e)}
    
    def generate_report(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        Generate comprehensive evaluation report
        
        Args:
            X: Test features
            y: True labels
            
        Returns:
            Dictionary with complete evaluation report
        """
        try:
            metrics = self.evaluate(X, y)
            
            if 'error' in metrics:
                return metrics
            
            # Add summary
            report = {
                'summary': {
                    'model_type': self.classifier.model_type,
                    'is_trained': self.classifier.is_trained,
                    'test_samples': len(X),
                    'overall_accuracy': metrics['accuracy'],
                    'precision': metrics['precision'],
                    'recall': metrics['recall'],
                    'f1_score': metrics['f1_score'],
                    'roc_auc': metrics['roc_auc']
                },
                'metrics': metrics,
                'confusion_matrix': self.get_confusion_matrix(X, y),
                'roc_curve': self.get_roc_curve(X, y),
                'pr_curve': self.get_precision_recall_curve(X, y)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {'error': str(e)}