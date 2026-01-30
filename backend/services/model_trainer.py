"""
Model training service for supervised ML classification
Handles training pipeline, hyperparameter tuning, and model selection
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, cross_val_score
from sklearn.metrics import make_scorer, f1_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from services.classifier import ClassificationDetector
from services.preprocessor import DataPreprocessor

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Service for training classification models
    """
    
    def __init__(self, config, classifier: ClassificationDetector,
                 preprocessor: DataPreprocessor, data_collector: Optional[Any] = None):
        """
        Initialize model trainer
        
        Args:
            config: Configuration object
            classifier: ClassificationDetector instance
            preprocessor: DataPreprocessor instance
            data_collector: DataCollector instance
        """
        self.config = config
        self.classifier = classifier
        self.preprocessor = preprocessor
        self.data_collector = data_collector
        self.training_history = []
        
        logger.info("ModelTrainer initialized")
    
    def load_training_data(self) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
        """
        Load ALL labeled training data from database or JSON file
        
        Returns:
            Tuple of (DataFrame with features and labels, None for compatibility)
        """
        try:
            from pathlib import Path
            import json
            import re
            
            # Check for preprocessed JSON file first (fallback for SSL issues)
            json_file = Path(__file__).parent.parent / 'data' / 'cicids2018_preprocessed_50k.json'
            max_samples = getattr(self.config, 'MAX_TRAINING_SAMPLES', None)
            
            if json_file.exists():
                logger.info(f"Found preprocessed JSON file: {json_file}")
                logger.info("Loading training data from JSON file (avoids MongoDB SSL issues)...")
                
                # Load from JSON file
                samples = []
                file_size_mb = json_file.stat().st_size / (1024 * 1024)
                logger.info(f"JSON file size: {file_size_mb:.2f} MB")
                
                try:
                    from tqdm import tqdm
                    TQDM_AVAILABLE = True
                except ImportError:
                    TQDM_AVAILABLE = False
                
                # Stream parse JSON (handles Infinity values)
                logger.info("Parsing JSON file...")
                with open(json_file, 'r', encoding='utf-8') as f:
                    # Skip opening bracket
                    char = f.read(1)
                    if char != '[':
                        raise ValueError("JSON file does not start with '['")
                    
                    buffer = ""
                    depth = 0
                    in_string = False
                    escape_next = False
                    
                    # Don't use tqdm for streaming - we don't know total count
                    sample_count = 0
                    
                    while True:
                        char = f.read(1)
                        if not char:
                            break
                        
                        if char == '\\' and not escape_next:
                            buffer += char
                            escape_next = True
                            continue
                        
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            buffer += char
                            continue
                        
                        escape_next = False
                        
                        if not in_string:
                            if char == '{':
                                depth += 1
                                buffer += char
                            elif char == '}':
                                depth -= 1
                                buffer += char
                                if depth == 0:
                                    # Complete sample found
                                    try:
                                        # Replace Infinity values before parsing
                                        fixed_buffer = re.sub(r':\s*Infinity\b', ': 0', buffer.strip().rstrip(','))
                                        fixed_buffer = re.sub(r':\s*\+Infinity\b', ': 0', fixed_buffer)
                                        fixed_buffer = re.sub(r':\s*-Infinity\b', ': 0', fixed_buffer)
                                        sample = json.loads(fixed_buffer)
                                        
                                        # Convert to format expected by training
                                        if 'features' in sample and 'label' in sample:
                                            samples.append({
                                                'label': sample['label'],
                                                **sample['features']
                                            })
                                            sample_count += 1
                                            
                                            # Log progress every 10000 samples
                                            if sample_count % 10000 == 0:
                                                logger.info(f"Loaded {sample_count:,} samples...")
                                        
                                        # Don't break early - load all samples first, then filter
                                        buffer = ""
                                        # Skip comma and whitespace
                                        while True:
                                            peek = f.read(1)
                                            if not peek or peek == ']':
                                                break
                                            if peek not in [' ', '\n', '\t', ',']:
                                                f.seek(f.tell() - 1)
                                                break
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"Error parsing sample: {e}")
                                        buffer = ""
                                        continue
                            else:
                                buffer += char
                        else:
                            buffer += char
                    
                
                logger.info(f"Loaded {len(samples):,} total samples from JSON file")
                
                # Separate by label and apply max_samples limit with 60:40 ratio
                benign_samples = [s for s in samples if s.get('label') == 'benign']
                malicious_samples = [s for s in samples if s.get('label') == 'malicious']
                
                logger.info(f"Found {len(benign_samples):,} benign and {len(malicious_samples):,} malicious samples")
                
                # Validate expected 50K samples (30K benign, 20K malicious)
                expected_benign = 30000
                expected_malicious = 20000
                if len(benign_samples) < expected_benign or len(malicious_samples) < expected_malicious:
                    logger.warning(f"Expected at least {expected_benign:,} benign and {expected_malicious:,} malicious samples")
                    logger.warning(f"Actual: {len(benign_samples):,} benign, {len(malicious_samples):,} malicious")
                
                # Apply max_samples limit if specified, maintaining 60:40 ratio
                if max_samples:
                    benign_limit = int(max_samples * 0.6)
                    malicious_limit = int(max_samples * 0.4)
                    
                    # Take first N samples of each class (they're already in order from JSON)
                    benign_samples = benign_samples[:benign_limit]
                    malicious_samples = malicious_samples[:malicious_limit]
                    
                    logger.info(f"Limiting to {max_samples:,} samples (60:40 ratio)")
                    logger.info(f"Selected {len(benign_samples):,} benign and {len(malicious_samples):,} malicious samples")
                else:
                    # Use all available samples, but ensure we have at least the expected amounts
                    if len(benign_samples) >= expected_benign and len(malicious_samples) >= expected_malicious:
                        # Use exactly 30K benign and 20K malicious for consistency
                        benign_samples = benign_samples[:expected_benign]
                        malicious_samples = malicious_samples[:expected_malicious]
                        logger.info(f"Using exactly {expected_benign:,} benign and {expected_malicious:,} malicious samples (50K total)")
                
                samples = benign_samples + malicious_samples
                
                if not samples:
                    raise ValueError("No labeled training data found in JSON file")
                
                # Data quality checks: Remove samples with too many missing values
                logger.info("Performing data quality checks...")
                initial_count = len(samples)
                quality_checked_samples = []
                for sample in samples:
                    # Count non-label features
                    feature_count = sum(1 for k, v in sample.items() if k != 'label' and v is not None)
                    total_features = len([k for k in sample.keys() if k != 'label'])
                    if total_features > 0:
                        missing_ratio = 1.0 - (feature_count / total_features)
                        if missing_ratio <= 0.5:  # Keep samples with <=50% missing values
                            quality_checked_samples.append(sample)
                
                removed_count = initial_count - len(quality_checked_samples)
                if removed_count > 0:
                    logger.info(f"Removed {removed_count:,} samples with >50% missing values")
                
                samples = quality_checked_samples
                logger.info(f"After quality checks: {len(samples):,} samples remaining")
                
                # Convert to DataFrame
                logger.info(f"Converting {len(samples):,} samples to DataFrame...")
                df = pd.DataFrame(samples)
                
                # Remove duplicates
                initial_df_size = len(df)
                df = df.drop_duplicates()
                duplicates_removed = initial_df_size - len(df)
                if duplicates_removed > 0:
                    logger.info(f"Removed {duplicates_removed:,} duplicate samples")
                
                # Shuffle the dataframe
                logger.info("Shuffling dataset...")
                df = df.sample(frac=1, random_state=42).reset_index(drop=True)
                
                # Check class balance
                if 'label' in df.columns:
                    label_counts = df['label'].value_counts()
                    total = len(df)
                    logger.info("="*60)
                    logger.info("Final Training Data Distribution:")
                    logger.info("="*60)
                    for label, count in label_counts.items():
                        percentage = (count / total) * 100
                        logger.info(f"  {label}: {count:,} ({percentage:.2f}%)")
                    logger.info(f"  Total: {total:,} samples")
                    logger.info("="*60)
                    
                    # Validate 60:40 ratio (with tolerance)
                    if 'benign' in label_counts and 'malicious' in label_counts:
                        benign_count = label_counts['benign']
                        malicious_count = label_counts['malicious']
                        benign_ratio = benign_count / total
                        if 0.55 <= benign_ratio <= 0.65:  # Allow 55-65% range
                            logger.info(f"✓ Class ratio validated: {benign_ratio:.2%} benign (target: 60%)")
                        else:
                            logger.warning(f"⚠ Class ratio: {benign_ratio:.2%} benign (target: 60%)")
                
                return df, None
            
            # Fallback to MongoDB loading
            if self.data_collector is None:
                raise ValueError(
                    "No preprocessed JSON file found and data_collector is None. "
                    "Place cicids2018_preprocessed_50k.json in backend/data/ or provide a DataCollector."
                )
            # Check if batch loading is enabled
            # Temporarily disable batch loading due to SSL issues with Python 3.14
            batch_loading = False  # getattr(self.config, 'BATCH_LOADING_ENABLED', False)
            
            if batch_loading:
                # Use batch loading for memory efficiency
                logger.info("Using batch loading for memory efficiency...")
                samples = []
                batch_size = 100000
                
                try:
                    from tqdm import tqdm
                    TQDM_AVAILABLE = True
                except ImportError:
                    TQDM_AVAILABLE = False
                
                # Load all benign samples in batches
                logger.info("Loading benign samples...")
                benign_batches = self.data_collector.get_all_labeled_samples_batch(
                    label='benign', batch_size=batch_size
                )
                benign_count = 0
                for batch in tqdm(benign_batches, desc="Benign samples", unit="batch") if TQDM_AVAILABLE else benign_batches:
                    samples.extend(batch)
                    benign_count += len(batch)
                    if max_samples and len(samples) >= max_samples:
                        samples = samples[:max_samples]
                        break
                
                # Load all malicious samples in batches
                logger.info("Loading malicious samples...")
                malicious_batches = self.data_collector.get_all_labeled_samples_batch(
                    label='malicious', batch_size=batch_size
                )
                malicious_count = 0
                for batch in tqdm(malicious_batches, desc="Malicious samples", unit="batch") if TQDM_AVAILABLE else malicious_batches:
                    samples.extend(batch)
                    malicious_count += len(batch)
                    if max_samples and len(samples) >= max_samples:
                        samples = samples[:max_samples]
                        break
                
                logger.info(f"Loaded {benign_count:,} benign and {malicious_count:,} malicious samples")
            else:
                # Load samples directly with limit to avoid timeouts
                logger.info("Loading samples from database...")
                
                # Calculate sample limits to maintain 60:40 ratio (benign:malicious)
                if max_samples:
                    # Maintain 60:40 ratio
                    benign_limit = int(max_samples * 0.6)
                    malicious_limit = int(max_samples * 0.4)
                    logger.info(f"Loading {benign_limit:,} benign and {malicious_limit:,} malicious samples (total: {max_samples:,})")
                else:
                    benign_limit = None
                    malicious_limit = None
                    logger.info("Loading all samples (this may take a while)...")
                
                # Load with timeout handling
                import time
                max_retries = 3
                benign_samples = []
                malicious_samples = []
                
                for attempt in range(max_retries):
                    try:
                        if not benign_samples:
                            benign_samples = self.data_collector.get_labeled_samples(label='benign', limit=benign_limit)
                        if not malicious_samples:
                            malicious_samples = self.data_collector.get_labeled_samples(label='malicious', limit=malicious_limit)
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Error loading samples (attempt {attempt + 1}/{max_retries}), retrying...: {e}")
                            time.sleep(2)
                            # Reconnect
                            from models.db_models import get_db
                            self.data_collector.db = get_db(self.config)
                            self.data_collector.training_collection = self.data_collector.db['training_data']
                        else:
                            logger.error(f"Failed to load samples after {max_retries} attempts: {e}")
                            raise
                
                samples = benign_samples + malicious_samples
                logger.info(f"Loaded {len(benign_samples):,} benign and {len(malicious_samples):,} malicious samples")
            
            if not samples:
                raise ValueError("No labeled training data found")
            
            # Apply max_samples limit if specified
            if max_samples and len(samples) > max_samples:
                logger.info(f"Limiting to {max_samples:,} samples as specified in config")
                samples = samples[:max_samples]
            
            # Convert to DataFrame with progress tracking
            logger.info(f"Converting {len(samples):,} samples to DataFrame...")
            try:
                from tqdm import tqdm
                TQDM_AVAILABLE = True
            except ImportError:
                TQDM_AVAILABLE = False
            
            data_list = []
            sample_iter = tqdm(samples, desc="Converting samples", unit="samples") if TQDM_AVAILABLE else samples
            
            for sample in sample_iter:
                row = {
                    'label': sample.get('label'),
                    **sample.get('features', {})
                }
                data_list.append(row)
            
            df = pd.DataFrame(data_list)
            
            # Shuffle the dataframe
            logger.info("Shuffling dataset...")
            df = df.sample(frac=1, random_state=42).reset_index(drop=True)
            
            # Check class balance
            if 'label' in df.columns:
                label_counts = df['label'].value_counts()
                total = len(df)
                logger.info(f"Training data distribution:")
                for label, count in label_counts.items():
                    percentage = (count / total) * 100
                    logger.info(f"  {label}: {count:,} ({percentage:.2f}%)")
            
            return df, None
            
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            raise
    
    def train_model(self, hyperparameter_tuning: bool = False) -> Dict[str, Any]:
        """
        Train the classification model
        
        Args:
            hyperparameter_tuning: Whether to perform hyperparameter tuning
            
        Returns:
            Dictionary with training results
        """
        try:
            # SecIDS-CNN is pre-trained; skip training
            if getattr(self.classifier, 'model_type', None) == 'secids_cnn':
                logger.info("SecIDS-CNN is a pre-trained model; training is not performed.")
                return {
                    'model_type': 'secids_cnn',
                    'training_samples': 0,
                    'validation_samples': 0,
                    'test_samples': 0,
                    'training_time': 0.0,
                    'message': 'SecIDS-CNN is pre-trained. Use evaluation endpoints to assess performance.',
                    'test_metrics': {}
                }
            start_time = datetime.now(timezone.utc)
            
            # Load training data
            logger.info("Loading training data...")
            df, _ = self.load_training_data()
            
            min_samples = getattr(self.config, 'MIN_TRAINING_SAMPLES_CLASSIFICATION', 1000)
            if len(df) < min_samples:
                raise ValueError(f"Insufficient training data: {len(df)} < {min_samples}")
            
            # Clean data
            logger.info("Cleaning data...")
            df_clean = self.preprocessor.clean_data(df)
            
            # Engineer features
            logger.info("Engineering features...")
            df_eng = self.preprocessor.engineer_features(df_clean)
            
            # Feature selection: reduce to top 50-60 features
            max_features = getattr(self.config, 'MAX_FEATURES', 60)
            logger.info(f"Applying feature selection (target: {max_features} features)...")
            df_selected = self.preprocessor.select_features_comprehensive(
                df_eng, 
                target_col='label',
                max_features=max_features,
                use_rf_importance=True
            )
            
            # Split data
            test_size = 1.0 - getattr(self.config, 'TRAIN_TEST_SPLIT_RATIO', 0.7)
            val_size = 0.15
            
            logger.info("Splitting data...")
            train_df, val_df, test_df = self.preprocessor.split_data(
                df_selected,
                test_size=test_size,
                val_size=val_size,
                stratify=True
            )
            
            # Prepare features and labels
            X_train = self.preprocessor.prepare_features(train_df)
            y_train = self.preprocessor.prepare_labels(train_df)
            
            X_val = self.preprocessor.prepare_features(val_df)
            y_val = self.preprocessor.prepare_labels(val_df)
            
            X_test = self.preprocessor.prepare_features(test_df)
            y_test = self.preprocessor.prepare_labels(test_df)
            
            # Apply SMOTE for class imbalance (only on training set)
            use_smote = getattr(self.config, 'USE_SMOTE', True)
            if use_smote:
                try:
                    from imblearn.over_sampling import SMOTE
                    logger.info("Applying SMOTE for class imbalance handling...")
                    logger.info(f"Before SMOTE - Class distribution: {np.bincount(y_train)}")
                    
                    # Use 'auto' to balance classes, or specify a ratio that makes sense
                    # 'auto' will balance to the majority class size
                    smote = SMOTE(random_state=42, sampling_strategy='auto')  # Balance to majority class
                    X_train, y_train = smote.fit_resample(X_train, y_train)
                    
                    logger.info(f"After SMOTE - Class distribution: {np.bincount(y_train)}")
                    logger.info(f"Training samples after SMOTE: {len(X_train):,}")
                except ImportError:
                    logger.warning("imbalanced-learn not installed. Install with: pip install imbalanced-learn")
                    logger.warning("Continuing without SMOTE...")
                except Exception as e:
                    logger.warning(f"Error applying SMOTE: {e}. Continuing without SMOTE...")
            
            # Get feature names from preprocessor
            feature_names = self.preprocessor.feature_names
            if feature_names is None:
                # Extract feature names from DataFrame
                feature_cols = self.preprocessor._get_feature_columns(train_df)
                feature_names = feature_cols
            
            # Hyperparameter tuning if requested
            best_params = None
            if hyperparameter_tuning:
                logger.info("Performing hyperparameter tuning...")
                best_params = self._tune_hyperparameters(X_train, y_train)
                logger.info(f"Best parameters: {best_params}")
                
                # Update classifier with best parameters
                if best_params:
                    logger.info("Updating classifier with best hyperparameters...")
                    if self.classifier.model_type == 'random_forest':
                        from sklearn.ensemble import RandomForestClassifier
                        # Use custom class weights favoring malicious detection
                        class_weight = {0: 0.4, 1: 0.6} if not use_smote else 'balanced'
                        self.classifier.model = RandomForestClassifier(
                            **best_params,
                            random_state=42,
                            class_weight=class_weight,
                            n_jobs=-1
                        )
                    elif self.classifier.model_type == 'xgboost':
                        try:
                            import xgboost as xgb
                            scale_pos_weight = best_params.pop('scale_pos_weight', 1.5)
                            self.classifier.model = xgb.XGBClassifier(
                                **best_params,
                                random_state=42,
                                n_jobs=-1,
                                scale_pos_weight=scale_pos_weight
                            )
                        except ImportError:
                            logger.warning("XGBoost not available")
                    elif self.classifier.model_type == 'svm':
                        from sklearn.svm import SVC
                        self.classifier.model = SVC(
                            **best_params,
                            probability=True,
                            random_state=42,
                            class_weight='balanced'
                        )
                    elif self.classifier.model_type == 'logistic_regression':
                        from sklearn.linear_model import LogisticRegression
                        self.classifier.model = LogisticRegression(
                            **best_params,
                            random_state=42,
                            class_weight='balanced',
                            n_jobs=-1
                        )
            else:
                logger.info("Using default hyperparameters")
                # Update class weights even without tuning
                if not use_smote:
                    if hasattr(self.classifier.model, 'class_weight'):
                        self.classifier.model.class_weight = {0: 0.4, 1: 0.6}
            
            # Train model with feature names
            logger.info("Training model...")
            self.classifier.train(X_train, y_train, X_val, y_val, feature_names=feature_names)
            
            # Perform 5-fold cross-validation for robust evaluation
            logger.info("Performing 5-fold cross-validation...")
            cv_metrics = self._cross_validate_model(X_train, y_train, cv_folds=5)
            logger.info(f"CV Accuracy: {cv_metrics.get('mean_accuracy', 0):.4f} (+/- {cv_metrics.get('std_accuracy', 0):.4f})")
            logger.info(f"CV F1-Score: {cv_metrics.get('mean_f1', 0):.4f} (+/- {cv_metrics.get('std_f1', 0):.4f})")
            logger.info(f"CV Recall: {cv_metrics.get('mean_recall', 0):.4f} (+/- {cv_metrics.get('std_recall', 0):.4f})")
            
            # Evaluate on test set
            logger.info("Evaluating model on test set...")
            from services.model_evaluator import ModelEvaluator
            evaluator = ModelEvaluator(self.classifier)
            test_metrics = evaluator.evaluate(X_test, y_test)
            
            # Calculate training time
            training_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Store training history
            training_record = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'training_samples': len(X_train),
                'validation_samples': len(X_val),
                'test_samples': len(X_test),
                'model_type': self.classifier.model_type,
                'test_metrics': test_metrics,
                'cv_metrics': cv_metrics,
                'training_time_seconds': training_time,
                'hyperparameters': best_params,
                'feature_count': len(feature_names) if feature_names else X_train.shape[1]
            }
            self.training_history.append(training_record)
            
            logger.info("="*60)
            logger.info("Training Summary")
            logger.info("="*60)
            logger.info(f"Training time: {training_time:.2f} seconds")
            logger.info(f"Feature count: {training_record['feature_count']}")
            logger.info(f"Test Accuracy: {test_metrics.get('accuracy', 0):.4f}")
            logger.info(f"Test Precision: {test_metrics.get('precision', 0):.4f}")
            logger.info(f"Test Recall: {test_metrics.get('recall', 0):.4f}")
            logger.info(f"Test F1-Score: {test_metrics.get('f1_score', 0):.4f}")
            logger.info(f"Test ROC-AUC: {test_metrics.get('roc_auc', 0):.4f}")
            logger.info("="*60)
            
            # Check success metrics
            self._check_success_metrics(test_metrics, cv_metrics)
            
            return training_record
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def _tune_hyperparameters(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        Perform hyperparameter tuning with RandomizedSearchCV
        
        Args:
            X: Training features
            y: Training labels
            
        Returns:
            Dictionary with best parameters
        """
        try:
            model_type = self.classifier.model_type
            
            # Get tuning parameters from config (increased defaults)
            n_iter = getattr(self.config, 'HYPERPARAMETER_TUNING_N_ITER', 50)  # Increased from 20
            cv_folds = getattr(self.config, 'HYPERPARAMETER_TUNING_CV', 5)  # Increased from 3
            
            if model_type == 'random_forest':
                # Expanded search space as per plan
                param_grid = {
                    'n_estimators': [200, 300, 500, 700, 1000],
                    'max_depth': [15, 20, 25, 30, None],
                    'min_samples_split': [2, 5, 10, 20],
                    'min_samples_leaf': [1, 2, 4, 8],
                    'max_features': ['sqrt', 'log2', 0.5, 0.7, None],
                    'bootstrap': [True, False],
                    'max_samples': [0.8, 0.9, 1.0]
                }
                # Use custom class weights if SMOTE not used
                use_smote = getattr(self.config, 'USE_SMOTE', True)
                class_weight = 'balanced' if use_smote else {0: 0.4, 1: 0.6}
                base_model = RandomForestClassifier(random_state=42, class_weight=class_weight, n_jobs=-1)
                
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
            
            elif model_type == 'xgboost':
                try:
                    import xgboost as xgb
                    param_grid = {
                        'n_estimators': [200, 300, 500, 700],
                        'max_depth': [4, 6, 8, 10],
                        'learning_rate': [0.01, 0.05, 0.1, 0.2],
                        'subsample': [0.7, 0.8, 0.9, 1.0],
                        'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
                        'min_child_weight': [1, 3, 5],
                        'gamma': [0, 0.1, 0.2],
                        'scale_pos_weight': [1.0, 1.5, 2.0]  # Handle class imbalance
                    }
                    use_smote = getattr(self.config, 'USE_SMOTE', True)
                    scale_pos_weight = 1.0 if use_smote else 1.5
                    base_model = xgb.XGBClassifier(random_state=42, n_jobs=-1, scale_pos_weight=scale_pos_weight)
                except ImportError:
                    logger.warning("XGBoost not available. Install with: pip install xgboost")
                    return {}
            
            else:
                logger.warning(f"Hyperparameter tuning not supported for {model_type}")
                return {}
            
            # Scale features using a temporary scaler (will be fit again in classifier.train())
            from sklearn.preprocessing import StandardScaler
            temp_scaler = StandardScaler()
            X_scaled = temp_scaler.fit_transform(X)
            
            # Use RandomizedSearchCV for faster tuning
            logger.info(f"Starting hyperparameter tuning with {n_iter} iterations and {cv_folds}-fold CV...")
            logger.info(f"Training on {len(X_scaled):,} samples...")
            logger.info("This may take several hours for large datasets...")
            
            # Optimize for F1-score (balances precision and recall)
            # Also create custom scorer that weights recall higher for IDS
            from sklearn.metrics import make_scorer, f1_score, recall_score
            f1_scorer = make_scorer(f1_score, average='binary')
            
            # Custom scorer: 0.6 * recall + 0.4 * f1 (favor recall for malicious detection)
            def custom_recall_f1_scorer(y_true, y_pred):
                f1 = f1_score(y_true, y_pred, average='binary', zero_division=0)
                recall = recall_score(y_true, y_pred, average='binary', zero_division=0)
                return 0.6 * recall + 0.4 * f1
            
            custom_scorer = make_scorer(custom_recall_f1_scorer)
            
            # Use F1 scorer (can switch to custom_scorer if needed)
            scorer = f1_scorer
            
            search = RandomizedSearchCV(
                base_model,
                param_grid,
                n_iter=n_iter,
                scoring=scorer,
                cv=cv_folds,
                n_jobs=-1,
                random_state=42,
                verbose=1
            )
            
            search.fit(X_scaled, y)
            
            logger.info(f"Hyperparameter tuning completed. Best score: {search.best_score_:.4f}")
            
            return search.best_params_
            
        except Exception as e:
            logger.error(f"Error tuning hyperparameters: {e}")
            return {}
    
    def _cross_validate_model(self, X: np.ndarray, y: np.ndarray, cv_folds: int = 5) -> Dict[str, Any]:
        """
        Perform cross-validation on trained model
        
        Args:
            X: Features
            y: Labels
            cv_folds: Number of CV folds
            
        Returns:
            Dictionary with CV metrics
        """
        try:
            from sklearn.model_selection import cross_val_score, cross_validate
            from sklearn.metrics import make_scorer, f1_score, recall_score, precision_score
            
            # Scale features
            X_scaled = self.preprocessor.scaler.transform(X)
            
            # Create custom scorers
            scoring = {
                'accuracy': 'accuracy',
                'f1': make_scorer(f1_score, average='binary', zero_division=0),
                'recall': make_scorer(recall_score, average='binary', zero_division=0),
                'precision': make_scorer(precision_score, average='binary', zero_division=0)
            }
            
            # Perform cross-validation
            cv_results = cross_validate(
                self.classifier.model,
                X_scaled,
                y,
                cv=cv_folds,
                scoring=scoring,
                n_jobs=-1,
                return_train_score=False
            )
            
            return {
                'cv_folds': cv_folds,
                'mean_accuracy': float(cv_results['test_accuracy'].mean()),
                'std_accuracy': float(cv_results['test_accuracy'].std()),
                'mean_f1': float(cv_results['test_f1'].mean()),
                'std_f1': float(cv_results['test_f1'].std()),
                'mean_recall': float(cv_results['test_recall'].mean()),
                'std_recall': float(cv_results['test_recall'].std()),
                'mean_precision': float(cv_results['test_precision'].mean()),
                'std_precision': float(cv_results['test_precision'].std()),
                'scores': {
                    'accuracy': cv_results['test_accuracy'].tolist(),
                    'f1': cv_results['test_f1'].tolist(),
                    'recall': cv_results['test_recall'].tolist(),
                    'precision': cv_results['test_precision'].tolist()
                }
            }
            
        except Exception as e:
            logger.error(f"Error performing cross-validation: {e}")
            return {'error': str(e)}
    
    def _check_success_metrics(self, test_metrics: Dict[str, Any], cv_metrics: Dict[str, Any]):
        """
        Check if success metrics are met
        
        Args:
            test_metrics: Test set metrics
            cv_metrics: Cross-validation metrics
        """
        logger.info("="*60)
        logger.info("Success Metrics Check")
        logger.info("="*60)
        
        accuracy = test_metrics.get('accuracy', 0)
        precision = test_metrics.get('precision', 0)
        recall = test_metrics.get('recall', 0)
        f1 = test_metrics.get('f1_score', 0)
        roc_auc = test_metrics.get('roc_auc', 0)
        
        success = True
        checks = {
            'Accuracy >= 90%': accuracy >= 0.90,
            'Precision >= 85%': precision >= 0.85,
            'Recall >= 85%': recall >= 0.85,
            'F1-Score >= 87%': f1 >= 0.87,
            'ROC-AUC >= 0.95': roc_auc >= 0.95
        }
        
        for metric, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"{status} {metric}")
            if not passed:
                success = False
        
        if success:
            logger.info("="*60)
            logger.info("✓ All success metrics met!")
            logger.info("="*60)
        else:
            logger.info("="*60)
            logger.warning("⚠ Some success metrics not met. Consider further optimization.")
            logger.info("="*60)
    
    def cross_validate(self, cv_folds: int = 5) -> Dict[str, Any]:
        """
        Perform cross-validation
        
        Args:
            cv_folds: Number of cross-validation folds
            
        Returns:
            Dictionary with CV results
        """
        try:
            # Load data
            df, _ = self.load_training_data()
            df_clean = self.preprocessor.clean_data(df)
            df_eng = self.preprocessor.engineer_features(df_clean)
            
            X = self.preprocessor.prepare_features(df_eng)
            y = self.preprocessor.prepare_labels(df_eng)
            
            # Scale features
            X_scaled = self.preprocessor.scaler.fit_transform(X)
            
            # Perform cross-validation
            scorer = make_scorer(f1_score, average='binary')
            cv_scores = cross_val_score(
                self.classifier.model,
                X_scaled,
                y,
                cv=cv_folds,
                scoring=scorer,
                n_jobs=-1
            )
            
            return {
                'cv_folds': cv_folds,
                'mean_score': float(cv_scores.mean()),
                'std_score': float(cv_scores.std()),
                'scores': cv_scores.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error performing cross-validation: {e}")
            return {'error': str(e)}
    
    def get_training_history(self) -> List[Dict[str, Any]]:
        """
        Get training history
        
        Returns:
            List of training records
        """
        return self.training_history