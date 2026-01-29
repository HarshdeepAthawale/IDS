"""
Supervised classification models for network traffic classification
Implements Random Forest, SVM, and Logistic Regression classifiers
"""

import logging
import numpy as np
import pickle
import os
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Try to import XGBoost (optional dependency)
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available. Install with: pip install xgboost")


def get_classification_detector(config):
    """
    Factory: return ClassificationDetector or SecIDSClassifierAdapter based on config.
    Use when CLASSIFICATION_MODEL_TYPE == 'secids_cnn' for the pre-trained SecIDS-CNN model.
    """
    model_type = getattr(config, 'CLASSIFICATION_MODEL_TYPE', None) or (config.get('CLASSIFICATION_MODEL_TYPE') if hasattr(config, 'get') else None) or 'random_forest'
    if model_type == 'secids_cnn':
        from services.secids_adapter import SecIDSClassifierAdapter
        return SecIDSClassifierAdapter(config)
    return ClassificationDetector(config)


class ClassificationDetector:
    """
    Supervised classification detector for benign/malicious traffic classification
    """
    
    def __init__(self, config):
        """
        Initialize classification detector
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_type = getattr(config, 'CLASSIFICATION_MODEL_TYPE', 'random_forest')
        self.model_path = 'classification_model.pkl'
        self.model_metadata = {}
        self.feature_names = None  # Will be set dynamically from training data
        self.optimal_threshold = 0.5  # Default threshold, can be tuned
        
        # Load existing model if available
        self._load_model()
        
        logger.info(f"ClassificationDetector initialized with model type: {self.model_type}")
    
    def _create_model(self, model_type: str = None):
        """
        Create a new model instance
        
        Args:
            model_type: Type of model to create
        """
        model_type = model_type or self.model_type
        
        if model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=200,  # Increased from 100 for better generalization
                max_depth=20,  # Increased from 10 to capture more patterns
                min_samples_split=2,  # Reduced from 5 to allow more splits
                min_samples_leaf=1,  # Reduced from 2 for more granular decisions
                random_state=42,
                n_jobs=-1,
                class_weight='balanced'  # Handle class imbalance
            )
        elif model_type == 'svm':
            self.model = SVC(
                kernel='rbf',
                C=1.0,
                gamma='scale',
                probability=True,
                random_state=42,
                class_weight='balanced'
            )
        elif model_type == 'logistic_regression':
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=42,
                class_weight='balanced',
                solver='lbfgs'
            )
        elif model_type == 'xgboost':
            if not XGBOOST_AVAILABLE:
                raise ValueError("XGBoost not available. Install with: pip install xgboost")
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                scale_pos_weight=1.5  # Handle class imbalance (favor malicious detection)
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        self.model_type = model_type
        logger.info(f"Created {model_type} model")
    
    def _load_model(self):
        """Load existing trained model"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data['model']
                    self.scaler = model_data.get('scaler', StandardScaler())
                    self.is_trained = model_data.get('is_trained', False)
                    self.model_type = model_data.get('model_type', self.model_type)
                    self.model_metadata = model_data.get('metadata', {})
                    self.feature_names = model_data.get('feature_names', None)
                    self.optimal_threshold = model_data.get('optimal_threshold', 0.5)
                    
                    logger.info(f"Loaded existing classification model: {self.model_type}")
                    if self.feature_names:
                        logger.info(f"Model has {len(self.feature_names)} features")
                    logger.info(f"Using threshold: {self.optimal_threshold:.3f}")
            else:
                # Create a new model instance
                self._create_model()
        except Exception as e:
            logger.warning(f"Could not load existing model: {e}")
            self._create_model()
    
    def _save_model(self):
        """Save trained model"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained,
                'model_type': self.model_type,
                'metadata': self.model_metadata,
                'feature_names': self.feature_names,  # Store feature names for dynamic handling
                'optimal_threshold': self.optimal_threshold,
                'timestamp': self.model_metadata.get('timestamp')
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Saved classification model: {self.model_type}")
        except Exception as e:
            logger.error(f"Could not save model: {e}")
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None,
              feature_names: Optional[List[str]] = None):
        """
        Train the classification model
        
        Args:
            X_train: Training features
            y_train: Training labels (0=benign, 1=malicious)
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            feature_names: List of feature names (optional, for dynamic feature handling)
        """
        try:
            if self.model is None:
                self._create_model()
            
            # Store feature names if provided
            if feature_names is not None:
                self.feature_names = feature_names
                logger.info(f"Training with {len(feature_names)} features")
            elif self.feature_names is None:
                # Create default feature names if not provided
                self.feature_names = [f'feature_{i}' for i in range(X_train.shape[1])]
                logger.info(f"Using default feature names ({len(self.feature_names)} features)")
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            
            # Train model
            logger.info(f"Training {self.model_type} model on {len(X_train)} samples...")
            self.model.fit(X_train_scaled, y_train)
            self.is_trained = True
            
            # Evaluate on validation set if provided
            if X_val is not None and y_val is not None:
                val_score = self.evaluate(X_val, y_val)
                self.model_metadata['validation_accuracy'] = val_score.get('accuracy', 0)
                logger.info(f"Validation accuracy: {self.model_metadata['validation_accuracy']:.4f}")
            
            # Find optimal threshold on validation set if provided
            if X_val is not None and y_val is not None:
                self._find_optimal_threshold(X_val, y_val)
            
            # Store training metadata
            self.model_metadata['training_samples'] = len(X_train)
            self.model_metadata['model_type'] = self.model_type
            self.model_metadata['feature_count'] = X_train.shape[1]
            self.model_metadata['optimal_threshold'] = self.optimal_threshold
            
            # Save model
            self._save_model()
            
            logger.info(f"Model training completed: {self.model_type}")
            logger.info(f"Optimal threshold: {self.optimal_threshold:.3f}")
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def predict(self, X: np.ndarray, threshold: float = None) -> np.ndarray:
        """
        Predict labels for given features
        
        Args:
            X: Feature matrix
            threshold: Decision threshold (default: self.optimal_threshold)
            
        Returns:
            Predicted labels (0=benign, 1=malicious)
        """
        try:
            if not self.is_trained:
                logger.warning("Model not trained, returning default predictions")
                return np.zeros(len(X))
            
            X_scaled = self.scaler.transform(X)
            
            # Use threshold if provided, otherwise use optimal threshold
            use_threshold = threshold if threshold is not None else self.optimal_threshold
            
            if use_threshold != 0.5:
                # Get probabilities and apply custom threshold
                probabilities = self.predict_proba(X_scaled)
                predictions = (probabilities[:, 1] >= use_threshold).astype(int)
            else:
                # Use default model prediction
                predictions = self.model.predict(X_scaled)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return np.zeros(len(X))
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities
        
        Args:
            X: Feature matrix
            
        Returns:
            Probability matrix [P(benign), P(malicious)]
        """
        try:
            if not self.is_trained:
                logger.warning("Model not trained, returning default probabilities")
                return np.array([[1.0, 0.0]] * len(X))
            
            X_scaled = self.scaler.transform(X)
            
            # Check if model supports predict_proba
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(X_scaled)
            else:
                # Fallback: use decision function
                decision = self.model.decision_function(X_scaled)
                # Convert to probabilities using sigmoid
                probabilities = 1 / (1 + np.exp(-decision))
                probabilities = np.column_stack([1 - probabilities, probabilities])
            
            return probabilities
            
        except Exception as e:
            logger.error(f"Error predicting probabilities: {e}")
            return np.array([[1.0, 0.0]] * len(X))
    
    def classify(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Classify a single sample based on features
        
        Args:
            features: Dictionary with feature values (supports dynamic feature count)
            
        Returns:
            Classification result with label and confidence
        """
        try:
            if not self.is_trained:
                return {
                    'label': 'unknown',
                    'confidence': 0.0,
                    'is_trained': False
                }
            
            # Use stored feature names if available, otherwise use all keys from features dict
            if self.feature_names:
                feature_names = self.feature_names
            else:
                # Fallback: use all keys from features dict, sorted for consistency
                feature_names = sorted(features.keys())
                logger.warning("No feature names stored in model, using features dict keys")
            
            # Extract features in correct order, defaulting to 0.0 for missing features
            feature_vector = np.array([[features.get(name, 0.0) for name in feature_names]])
            
            # Validate feature count matches model expectations
            if len(feature_names) != self.model.n_features_in_:
                # Pad or truncate if needed (this is expected for dynamic feature extraction)
                if len(feature_names) < self.model.n_features_in_:
                    # Pad with zeros
                    padding = np.zeros((1, self.model.n_features_in_ - len(feature_names)))
                    feature_vector = np.hstack([feature_vector, padding])
                    logger.debug(f"Padded features: {len(feature_names)} -> {self.model.n_features_in_}")
                elif len(feature_names) > self.model.n_features_in_:
                    # Truncate to match model
                    feature_vector = feature_vector[:, :self.model.n_features_in_]
                    logger.debug(f"Truncated features: {len(feature_names)} -> {self.model.n_features_in_}")
            
            # Get prediction and probability
            prediction = self.predict(feature_vector)[0]
            probabilities = self.predict_proba(feature_vector)[0]
            
            # Determine label and confidence
            label = 'malicious' if prediction == 1 else 'benign'
            confidence = float(probabilities[1] if prediction == 1 else probabilities[0])
            
            return {
                'label': label,
                'confidence': confidence,
                'is_trained': True,
                'probabilities': {
                    'benign': float(probabilities[0]),
                    'malicious': float(probabilities[1])
                }
            }
            
        except Exception as e:
            logger.error(f"Error classifying sample: {e}")
            return {
                'label': 'unknown',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Evaluate model performance
        
        Args:
            X: Test features
            y: True labels
            
        Returns:
            Dictionary with evaluation metrics
        """
        try:
            if not self.is_trained:
                return {'error': 'Model not trained'}
            
            predictions = self.predict(X)
            
            # Calculate metrics
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score,
                f1_score, confusion_matrix
            )
            
            accuracy = accuracy_score(y, predictions)
            precision = precision_score(y, predictions, zero_division=0)
            recall = recall_score(y, predictions, zero_division=0)
            f1 = f1_score(y, predictions, zero_division=0)
            
            cm = confusion_matrix(y, predictions)
            
            metrics = {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'confusion_matrix': cm.tolist()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return {'error': str(e)}
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance (for tree-based models)
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        try:
            if not self.is_trained or not hasattr(self.model, 'feature_importances_'):
                return {}
            
            importances = self.model.feature_importances_
            
            # Use stored feature names if available, otherwise create default names
            if self.feature_names and len(self.feature_names) == len(importances):
                feature_names = self.feature_names
            else:
                # Fallback: create default feature names
                feature_names = [f'feature_{i}' for i in range(len(importances))]
                logger.warning(f"Using default feature names (expected {len(importances)} features)")
            
            importance_dict = {
                name: float(importance)
                for name, importance in zip(feature_names, importances)
            }
            
            # Sort by importance
            importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            
            return importance_dict
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {}
    
    def _find_optimal_threshold(self, X_val: np.ndarray, y_val: np.ndarray):
        """
        Find optimal threshold using ROC curve to maximize F1-score with recall bias
        
        Args:
            X_val: Validation features
            y_val: Validation labels
        """
        try:
            from sklearn.metrics import roc_curve, f1_score
            
            probabilities = self.predict_proba(X_val)
            fpr, tpr, thresholds = roc_curve(y_val, probabilities[:, 1])
            
            # Find threshold that maximizes F1-score (with recall bias)
            best_threshold = 0.5
            best_f1 = 0.0
            
            for threshold in thresholds:
                if 0.1 <= threshold <= 0.9:  # Reasonable range
                    predictions = (probabilities[:, 1] >= threshold).astype(int)
                    f1 = f1_score(y_val, predictions, zero_division=0)
                    
                    # Weight recall more heavily for IDS (malicious detection is critical)
                    from sklearn.metrics import recall_score, precision_score
                    recall = recall_score(y_val, predictions, zero_division=0)
                    precision = precision_score(y_val, predictions, zero_division=0)
                    
                    # Combined score: 60% recall + 40% F1 (favor recall)
                    combined_score = 0.6 * recall + 0.4 * f1
                    
                    if combined_score > best_f1:
                        best_f1 = combined_score
                        best_threshold = threshold
            
            self.optimal_threshold = float(best_threshold)
            logger.info(f"Optimal threshold found: {self.optimal_threshold:.3f} (F1-weighted score: {best_f1:.4f})")
            
        except Exception as e:
            logger.warning(f"Error finding optimal threshold: {e}. Using default 0.5")
            self.optimal_threshold = 0.5
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model information
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_type': self.model_type,
            'is_trained': self.is_trained,
            'model_path': self.model_path,
            'metadata': self.model_metadata,
            'optimal_threshold': self.optimal_threshold
        }