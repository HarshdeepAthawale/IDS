"""
Standalone training module for Google Colab
Adapted from backend services to work without Flask dependencies
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, make_scorer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ColabConfig:
    """Simplified config class for Colab (no Flask dependencies)"""
    
    def __init__(self, mongodb_uri: str, mongodb_database_name: str = 'ids_db', **kwargs):
        self.MONGODB_URI = mongodb_uri
        self.MONGODB_DATABASE_NAME = mongodb_database_name
        self.CLASSIFICATION_MODEL_TYPE = kwargs.get('CLASSIFICATION_MODEL_TYPE', 'random_forest')
        self.MIN_TRAINING_SAMPLES_CLASSIFICATION = kwargs.get('MIN_TRAINING_SAMPLES_CLASSIFICATION', 1000)
        self.TRAIN_TEST_SPLIT_RATIO = kwargs.get('TRAIN_TEST_SPLIT_RATIO', 0.7)
        self.HYPERPARAMETER_TUNING_ENABLED = kwargs.get('HYPERPARAMETER_TUNING_ENABLED', True)
        self.HYPERPARAMETER_TUNING_N_ITER = kwargs.get('HYPERPARAMETER_TUNING_N_ITER', 20)
        self.HYPERPARAMETER_TUNING_CV = kwargs.get('HYPERPARAMETER_TUNING_CV', 3)
        self.MAX_TRAINING_SAMPLES = kwargs.get('MAX_TRAINING_SAMPLES', None)
        self.BATCH_LOADING_ENABLED = kwargs.get('BATCH_LOADING_ENABLED', True)


class ColabDataCollector:
    """Data collector for Colab (MongoDB connection only)"""
    
    def __init__(self, config: ColabConfig):
        self.config = config
        try:
            self.client = MongoClient(
                config.MONGODB_URI,
                serverSelectionTimeoutMS=10000  # 10 second timeout
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[config.MONGODB_DATABASE_NAME]
            self.training_collection = self.db['training_data']
            logger.info(f"Connected to MongoDB: {config.MONGODB_DATABASE_NAME}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def get_labeled_samples(self, label: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get labeled training samples"""
        try:
            query = {'label': {'$ne': None}}
            if label:
                query['label'] = label
            
            cursor = self.training_collection.find(query).sort('timestamp', -1)
            if limit is not None:
                cursor = cursor.limit(limit)
            
            return list(cursor)
        except Exception as e:
            logger.error(f"Error getting labeled samples: {e}")
            return []
    
    def get_all_labeled_samples_batch(self, label: Optional[str] = None, 
                                     batch_size: int = 100000):
        """Get all labeled samples in batches"""
        try:
            query = {'label': {'$ne': None}}
            if label:
                query['label'] = label
            
            cursor = self.training_collection.find(query).sort('timestamp', -1)
            batch = []
            for sample in cursor:
                batch.append(sample)
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            if batch:
                yield batch
        except Exception as e:
            logger.error(f"Error getting labeled samples in batches: {e}")
            yield []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about training data"""
        try:
            total_samples = self.training_collection.count_documents({})
            labeled_samples = self.training_collection.count_documents({'label': {'$ne': None}})
            benign_count = self.training_collection.count_documents({'label': 'benign'})
            malicious_count = self.training_collection.count_documents({'label': 'malicious'})
            
            return {
                'total_samples': total_samples,
                'labeled_samples': labeled_samples,
                'benign_count': benign_count,
                'malicious_count': malicious_count,
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


class ColabDataPreprocessor:
    """Data preprocessor for Colab"""
    
    def __init__(self, config: Optional[ColabConfig] = None):
        self.config = config
        self.scaler = StandardScaler()
        self.feature_names = None
        logger.info("ColabDataPreprocessor initialized")
    
    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get feature column names"""
        exclude_cols = ['label', 'source_ip', 'dest_ip', 'protocol', 'dst_port', 
                       'timestamp', 'labeled_by', 'confidence', 'metadata', '_id']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        if self.feature_names is None or set(self.feature_names) != set(feature_cols):
            self.feature_names = feature_cols
            logger.info(f"Detected {len(feature_cols)} features")
        return feature_cols
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean training data"""
        try:
            df_clean = df.copy()
            feature_cols = self._get_feature_columns(df_clean)
            
            if not feature_cols:
                logger.warning("No feature columns found")
                return df_clean
            
            # Remove duplicates
            initial_count = len(df_clean)
            df_clean = df_clean.drop_duplicates()
            duplicates_removed = initial_count - len(df_clean)
            if duplicates_removed > 0:
                logger.info(f"Removed {duplicates_removed} duplicate samples")
            
            # Remove constant features
            constant_features = []
            for feature in feature_cols:
                if feature in df_clean.columns:
                    if df_clean[feature].nunique() <= 1:
                        constant_features.append(feature)
            
            if constant_features:
                logger.info(f"Removing {len(constant_features)} constant features")
                df_clean = df_clean.drop(columns=constant_features)
                feature_cols = [f for f in feature_cols if f not in constant_features]
            
            # Handle missing values
            numeric_features = []
            for feature in feature_cols:
                if feature in df_clean.columns:
                    if pd.api.types.is_numeric_dtype(df_clean[feature]):
                        numeric_features.append(feature)
            
            for feature in numeric_features:
                if df_clean[feature].isna().any():
                    median_value = df_clean[feature].median()
                    if pd.isna(median_value):
                        median_value = 0.0
                    df_clean[feature].fillna(median_value, inplace=True)
            
            # Remove rows with missing labels
            if 'label' in df_clean.columns:
                before_count = len(df_clean)
                df_clean = df_clean.dropna(subset=['label'])
                removed = before_count - len(df_clean)
                if removed > 0:
                    logger.info(f"Removed {removed} samples with missing labels")
            
            # Handle outliers using IQR method
            for feature in numeric_features:
                if feature in df_clean.columns:
                    Q1 = df_clean[feature].quantile(0.25)
                    Q3 = df_clean[feature].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    if IQR > 0:
                        lower_bound = Q1 - 3 * IQR
                        upper_bound = Q3 + 3 * IQR
                        df_clean[feature] = df_clean[feature].clip(lower=lower_bound, upper=upper_bound)
            
            return df_clean
        except Exception as e:
            logger.error(f"Error cleaning data: {e}")
            return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create derived features"""
        try:
            df_eng = df.copy()
            # Add feature engineering logic here if needed
            return df_eng
        except Exception as e:
            logger.error(f"Error engineering features: {e}")
            return df
    
    def split_data(self, df: pd.DataFrame, test_size: float = 0.15,
                  val_size: float = 0.15, stratify: bool = True,
                  random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split data into train, validation, and test sets"""
        try:
            if 'label' not in df.columns:
                raise ValueError("DataFrame must contain 'label' column")
            
            stratify_col = df['label'] if stratify else None
            train_val_df, test_df = train_test_split(
                df, test_size=test_size, stratify=stratify_col, random_state=random_state
            )
            
            adjusted_val_size = val_size / (1 - test_size)
            stratify_col = train_val_df['label'] if stratify else None
            train_df, val_df = train_test_split(
                train_val_df, test_size=adjusted_val_size, stratify=stratify_col, random_state=random_state
            )
            
            logger.info(f"Data split: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")
            return train_df, val_df, test_df
        except Exception as e:
            logger.error(f"Error splitting data: {e}")
            raise
    
    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare feature matrix from DataFrame"""
        try:
            feature_cols = self._get_feature_columns(df)
            if not feature_cols:
                raise ValueError("No feature columns found in DataFrame")
            
            numeric_cols = []
            for col in feature_cols:
                if col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        numeric_cols.append(col)
                    else:
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            numeric_cols.append(col)
                        except:
                            logger.warning(f"Skipping non-numeric feature: {col}")
            
            if not numeric_cols:
                raise ValueError("No numeric feature columns found")
            
            X = df[numeric_cols].values
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            return X
        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            raise
    
    def prepare_labels(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare label array from DataFrame"""
        try:
            if 'label' not in df.columns:
                raise ValueError("DataFrame must contain 'label' column")
            y = df['label'].map({'benign': 0, 'malicious': 1}).values
            return y
        except Exception as e:
            logger.error(f"Error preparing labels: {e}")
            raise


class ColabClassifier:
    """Classification detector for Colab"""
    
    def __init__(self, config: ColabConfig):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_type = config.CLASSIFICATION_MODEL_TYPE
        self.feature_names = None
        self._create_model()
        logger.info(f"ColabClassifier initialized with model type: {self.model_type}")
    
    def _create_model(self):
        """Create a new model instance"""
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100, max_depth=10, min_samples_split=5,
                min_samples_leaf=2, random_state=42, n_jobs=-1,
                class_weight='balanced'
            )
        elif self.model_type == 'svm':
            self.model = SVC(
                kernel='rbf', C=1.0, gamma='scale', probability=True,
                random_state=42, class_weight='balanced'
            )
        elif self.model_type == 'logistic_regression':
            self.model = LogisticRegression(
                max_iter=1000, random_state=42, class_weight='balanced',
                solver='lbfgs', n_jobs=-1
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None,
              feature_names: Optional[List[str]] = None):
        """Train the classification model"""
        try:
            if feature_names is not None:
                self.feature_names = feature_names
            elif self.feature_names is None:
                self.feature_names = [f'feature_{i}' for i in range(X_train.shape[1])]
            
            X_train_scaled = self.scaler.fit_transform(X_train)
            logger.info(f"Training {self.model_type} model on {len(X_train)} samples...")
            self.model.fit(X_train_scaled, y_train)
            self.is_trained = True
            logger.info(f"Model training completed: {self.model_type}")
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict labels"""
        if not self.is_trained:
            return np.zeros(len(X))
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities"""
        if not self.is_trained:
            return np.array([[1.0, 0.0]] * len(X))
        X_scaled = self.scaler.transform(X)
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X_scaled)
        else:
            decision = self.model.decision_function(X_scaled)
            probabilities = 1 / (1 + np.exp(-decision))
            return np.column_stack([1 - probabilities, probabilities])
    
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Evaluate model performance"""
        try:
            if not self.is_trained:
                return {'error': 'Model not trained'}
            
            predictions = self.predict(X)
            probabilities = self.predict_proba(X)
            
            accuracy = accuracy_score(y, predictions)
            precision = precision_score(y, predictions, zero_division=0)
            recall = recall_score(y, predictions, zero_division=0)
            f1 = f1_score(y, predictions, zero_division=0)
            
            try:
                roc_auc = roc_auc_score(y, probabilities[:, 1])
            except:
                roc_auc = 0.0
            
            cm = confusion_matrix(y, predictions)
            
            return {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'roc_auc': float(roc_auc),
                'confusion_matrix': cm.tolist()
            }
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return {'error': str(e)}


class ColabModelTrainer:
    """Model trainer for Colab"""
    
    def __init__(self, config: ColabConfig, classifier: ColabClassifier,
                 preprocessor: ColabDataPreprocessor, data_collector: ColabDataCollector):
        self.config = config
        self.classifier = classifier
        self.preprocessor = preprocessor
        self.data_collector = data_collector
        self.training_history = []
        logger.info("ColabModelTrainer initialized")
    
    def load_training_data(self) -> pd.DataFrame:
        """Load ALL labeled training data from database"""
        try:
            batch_loading = self.config.BATCH_LOADING_ENABLED
            max_samples = self.config.MAX_TRAINING_SAMPLES
            
            if batch_loading:
                logger.info("Using batch loading for memory efficiency...")
                samples = []
                batch_size = 100000
                
                try:
                    from tqdm import tqdm
                    TQDM_AVAILABLE = True
                except ImportError:
                    TQDM_AVAILABLE = False
                
                # Load benign samples
                logger.info("Loading benign samples...")
                benign_batches = self.data_collector.get_all_labeled_samples_batch(
                    label='benign', batch_size=batch_size
                )
                for batch in tqdm(benign_batches, desc="Benign samples", unit="batch") if TQDM_AVAILABLE else benign_batches:
                    samples.extend(batch)
                    if max_samples and len(samples) >= max_samples:
                        samples = samples[:max_samples]
                        break
                
                # Load malicious samples
                logger.info("Loading malicious samples...")
                malicious_batches = self.data_collector.get_all_labeled_samples_batch(
                    label='malicious', batch_size=batch_size
                )
                for batch in tqdm(malicious_batches, desc="Malicious samples", unit="batch") if TQDM_AVAILABLE else malicious_batches:
                    samples.extend(batch)
                    if max_samples and len(samples) >= max_samples:
                        samples = samples[:max_samples]
                        break
                
                logger.info(f"Loaded {len(samples):,} total samples")
            else:
                logger.info("Loading all samples from database...")
                benign_samples = self.data_collector.get_labeled_samples(label='benign', limit=None)
                malicious_samples = self.data_collector.get_labeled_samples(label='malicious', limit=None)
                samples = benign_samples + malicious_samples
                logger.info(f"Loaded {len(benign_samples):,} benign and {len(malicious_samples):,} malicious samples")
            
            if not samples:
                raise ValueError("No labeled training data found")
            
            if max_samples and len(samples) > max_samples:
                logger.info(f"Limiting to {max_samples:,} samples")
                samples = samples[:max_samples]
            
            # Convert to DataFrame
            logger.info(f"Converting {len(samples):,} samples to DataFrame...")
            try:
                from tqdm import tqdm
                TQDM_AVAILABLE = True
            except ImportError:
                TQDM_AVAILABLE = False
            
            data_list = []
            for sample in tqdm(samples, desc="Converting samples", unit="samples") if TQDM_AVAILABLE else samples:
                row = {
                    'label': sample.get('label'),
                    **sample.get('features', {})
                }
                data_list.append(row)
            
            df = pd.DataFrame(data_list)
            
            # Shuffle
            logger.info("Shuffling dataset...")
            df = df.sample(frac=1, random_state=42).reset_index(drop=True)
            
            # Check class balance
            if 'label' in df.columns:
                label_counts = df['label'].value_counts()
                total = len(df)
                logger.info("Training data distribution:")
                for label, count in label_counts.items():
                    percentage = (count / total) * 100
                    logger.info(f"  {label}: {count:,} ({percentage:.2f}%)")
            
            return df
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            raise
    
    def _tune_hyperparameters(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Perform hyperparameter tuning"""
        try:
            model_type = self.classifier.model_type
            n_iter = self.config.HYPERPARAMETER_TUNING_N_ITER
            cv_folds = self.config.HYPERPARAMETER_TUNING_CV
            
            if model_type == 'random_forest':
                param_grid = {
                    'n_estimators': [100, 200, 300, 500],
                    'max_depth': [10, 20, 30, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4],
                    'max_features': ['sqrt', 'log2', None]
                }
                base_model = RandomForestClassifier(random_state=42, class_weight='balanced', n_jobs=-1)
            elif model_type == 'svm':
                param_grid = {
                    'C': [0.1, 1, 10, 100],
                    'gamma': ['scale', 'auto', 0.001, 0.01, 0.1],
                    'kernel': ['rbf', 'linear']
                }
                base_model = SVC(probability=True, random_state=42, class_weight='balanced')
            elif model_type == 'logistic_regression':
                param_grid = {
                    'C': [0.1, 1, 10, 100],
                    'solver': ['lbfgs', 'liblinear'],
                    'max_iter': [500, 1000, 2000]
                }
                base_model = LogisticRegression(random_state=42, class_weight='balanced', n_jobs=-1)
            else:
                logger.warning(f"Hyperparameter tuning not supported for {model_type}")
                return {}
            
            # Scale features
            from sklearn.preprocessing import StandardScaler
            temp_scaler = StandardScaler()
            X_scaled = temp_scaler.fit_transform(X)
            
            logger.info(f"Starting hyperparameter tuning with {n_iter} iterations and {cv_folds}-fold CV...")
            logger.info(f"Training on {len(X_scaled):,} samples...")
            
            scorer = make_scorer(f1_score, average='binary')
            search = RandomizedSearchCV(
                base_model, param_grid, n_iter=n_iter, scoring=scorer,
                cv=cv_folds, n_jobs=-1, random_state=42, verbose=1
            )
            
            search.fit(X_scaled, y)
            logger.info(f"Hyperparameter tuning completed. Best score: {search.best_score_:.4f}")
            return search.best_params_
        except Exception as e:
            logger.error(f"Error tuning hyperparameters: {e}")
            return {}
    
    def train_model(self, hyperparameter_tuning: bool = False) -> Dict[str, Any]:
        """Train the classification model"""
        try:
            start_time = datetime.utcnow()
            
            # Load training data
            logger.info("Loading training data...")
            df = self.load_training_data()
            
            min_samples = self.config.MIN_TRAINING_SAMPLES_CLASSIFICATION
            if len(df) < min_samples:
                raise ValueError(f"Insufficient training data: {len(df)} < {min_samples}")
            
            # Clean data
            logger.info("Cleaning data...")
            df_clean = self.preprocessor.clean_data(df)
            
            # Engineer features
            logger.info("Engineering features...")
            df_eng = self.preprocessor.engineer_features(df_clean)
            
            # Split data
            test_size = 1.0 - self.config.TRAIN_TEST_SPLIT_RATIO
            val_size = 0.15
            
            logger.info("Splitting data...")
            train_df, val_df, test_df = self.preprocessor.split_data(
                df_eng, test_size=test_size, val_size=val_size, stratify=True
            )
            
            # Prepare features and labels
            X_train = self.preprocessor.prepare_features(train_df)
            y_train = self.preprocessor.prepare_labels(train_df)
            
            X_val = self.preprocessor.prepare_features(val_df)
            y_val = self.preprocessor.prepare_labels(val_df)
            
            X_test = self.preprocessor.prepare_features(test_df)
            y_test = self.preprocessor.prepare_labels(test_df)
            
            # Get feature names
            feature_names = self.preprocessor.feature_names
            if feature_names is None:
                feature_cols = self.preprocessor._get_feature_columns(train_df)
                feature_names = feature_cols
            
            # Hyperparameter tuning
            best_params = None
            if hyperparameter_tuning:
                logger.info("Performing hyperparameter tuning...")
                best_params = self._tune_hyperparameters(X_train, y_train)
                logger.info(f"Best parameters: {best_params}")
                
                # Update classifier with best parameters
                if best_params and self.classifier.model_type == 'random_forest':
                    self.classifier.model = RandomForestClassifier(
                        **best_params, random_state=42, class_weight='balanced', n_jobs=-1
                    )
            else:
                logger.info("Using default hyperparameters")
            
            # Train model
            logger.info("Training model...")
            self.classifier.train(X_train, y_train, X_val, y_val, feature_names=feature_names)
            
            # Evaluate on test set
            logger.info("Evaluating model...")
            test_metrics = self.classifier.evaluate(X_test, y_test)
            
            # Calculate training time
            training_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Store training history
            training_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'training_samples': len(X_train),
                'validation_samples': len(X_val),
                'test_samples': len(X_test),
                'model_type': self.classifier.model_type,
                'test_metrics': test_metrics,
                'training_time_seconds': training_time,
                'hyperparameters': best_params
            }
            self.training_history.append(training_record)
            
            logger.info(f"Model training completed in {training_time:.2f} seconds")
            logger.info(f"Test accuracy: {test_metrics.get('accuracy', 0):.4f}")
            
            return training_record
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def save_model(self, filepath: str = 'classification_model.pkl'):
        """Save trained model"""
        try:
            import pickle
            model_data = {
                'model': self.classifier.model,
                'scaler': self.classifier.scaler,
                'is_trained': self.classifier.is_trained,
                'model_type': self.classifier.model_type,
                'feature_names': self.classifier.feature_names,
                'metadata': {
                    'training_samples': self.training_history[-1]['training_samples'] if self.training_history else 0,
                    'test_accuracy': self.training_history[-1]['test_metrics'].get('accuracy', 0) if self.training_history else 0,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise
