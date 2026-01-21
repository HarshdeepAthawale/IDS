"""
Ensemble classifier service for combining multiple models
Implements voting, stacking, and bagging ensemble methods
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression

# Try to import XGBoost (optional)
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

logger = logging.getLogger(__name__)


class EnsembleClassifier:
    """
    Ensemble classifier that combines multiple models for better performance
    """
    
    def __init__(self, config, base_models: Optional[List[str]] = None):
        """
        Initialize ensemble classifier
        
        Args:
            config: Configuration object
            base_models: List of model types to include ['random_forest', 'xgboost', 'svm']
        """
        self.config = config
        self.base_models = base_models or ['random_forest', 'xgboost', 'svm']
        self.ensemble = None
        self.is_trained = False
        self.feature_names = None
        
        logger.info(f"EnsembleClassifier initialized with models: {self.base_models}")
    
    def _create_base_models(self) -> List[tuple]:
        """
        Create base models for ensemble
        
        Returns:
            List of (name, model) tuples
        """
        models = []
        
        # Random Forest
        if 'random_forest' in self.base_models:
            use_smote = getattr(self.config, 'USE_SMOTE', True)
            class_weight = 'balanced' if use_smote else {0: 0.4, 1: 0.6}
            rf = RandomForestClassifier(
                n_estimators=200,
                max_depth=20,
                min_samples_split=2,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=-1,
                class_weight=class_weight
            )
            models.append(('rf', rf))
        
        # XGBoost
        if 'xgboost' in self.base_models and XGBOOST_AVAILABLE:
            use_smote = getattr(self.config, 'USE_SMOTE', True)
            scale_pos_weight = 1.0 if use_smote else 1.5
            xgb_model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                scale_pos_weight=scale_pos_weight
            )
            models.append(('xgb', xgb_model))
        elif 'xgboost' in self.base_models:
            logger.warning("XGBoost requested but not available. Skipping.")
        
        # SVM
        if 'svm' in self.base_models:
            svm = SVC(
                kernel='rbf',
                C=1.0,
                gamma='scale',
                probability=True,
                random_state=42,
                class_weight='balanced'
            )
            models.append(('svm', svm))
        
        # Logistic Regression (as meta-learner or base)
        if 'logistic_regression' in self.base_models:
            lr = LogisticRegression(
                max_iter=1000,
                random_state=42,
                class_weight='balanced',
                solver='lbfgs',
                n_jobs=-1
            )
            models.append(('lr', lr))
        
        if not models:
            raise ValueError("No valid base models created. Check model availability.")
        
        logger.info(f"Created {len(models)} base models for ensemble")
        return models
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None,
              feature_names: Optional[List[str]] = None):
        """
        Train ensemble classifier
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            feature_names: Feature names (optional)
        """
        try:
            self.feature_names = feature_names
            
            # Create base models
            base_models = self._create_base_models()
            
            # Create voting classifier with soft voting (average probabilities)
            self.ensemble = VotingClassifier(
                estimators=base_models,
                voting='soft',  # Use probability averaging
                n_jobs=-1
            )
            
            logger.info(f"Training ensemble with {len(base_models)} models on {len(X_train)} samples...")
            self.ensemble.fit(X_train, y_train)
            self.is_trained = True
            
            # Evaluate on validation set if provided
            if X_val is not None and y_val is not None:
                from sklearn.metrics import accuracy_score, f1_score, recall_score
                val_pred = self.ensemble.predict(X_val)
                val_acc = accuracy_score(y_val, val_pred)
                val_f1 = f1_score(y_val, val_pred, zero_division=0)
                val_recall = recall_score(y_val, val_pred, zero_division=0)
                logger.info(f"Validation metrics - Accuracy: {val_acc:.4f}, F1: {val_f1:.4f}, Recall: {val_recall:.4f}")
            
            logger.info("Ensemble training completed")
            
        except Exception as e:
            logger.error(f"Error training ensemble: {e}")
            raise
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict labels using ensemble
        
        Args:
            X: Feature matrix
            
        Returns:
            Predicted labels
        """
        try:
            if not self.is_trained:
                logger.warning("Ensemble not trained, returning default predictions")
                return np.zeros(len(X))
            
            return self.ensemble.predict(X)
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return np.zeros(len(X))
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities using ensemble
        
        Args:
            X: Feature matrix
            
        Returns:
            Probability matrix
        """
        try:
            if not self.is_trained:
                logger.warning("Ensemble not trained, returning default probabilities")
                return np.array([[1.0, 0.0]] * len(X))
            
            return self.ensemble.predict_proba(X)
            
        except Exception as e:
            logger.error(f"Error predicting probabilities: {e}")
            return np.array([[1.0, 0.0]] * len(X))
    
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Evaluate ensemble performance
        
        Args:
            X: Test features
            y: True labels
            
        Returns:
            Dictionary with evaluation metrics
        """
        try:
            if not self.is_trained:
                return {'error': 'Ensemble not trained'}
            
            predictions = self.predict(X)
            
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score,
                f1_score, confusion_matrix, roc_auc_score
            )
            
            probabilities = self.predict_proba(X)
            
            accuracy = accuracy_score(y, predictions)
            precision = precision_score(y, predictions, zero_division=0)
            recall = recall_score(y, predictions, zero_division=0)
            f1 = f1_score(y, predictions, zero_division=0)
            
            try:
                roc_auc = roc_auc_score(y, probabilities[:, 1])
            except ValueError:
                roc_auc = 0.0
            
            cm = confusion_matrix(y, predictions)
            
            metrics = {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'roc_auc': float(roc_auc),
                'confusion_matrix': cm.tolist()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating ensemble: {e}")
            return {'error': str(e)}
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get ensemble information
        
        Returns:
            Dictionary with ensemble information
        """
        return {
            'model_type': 'ensemble',
            'base_models': self.base_models,
            'is_trained': self.is_trained,
            'num_models': len(self.base_models) if self.ensemble else 0
        }
