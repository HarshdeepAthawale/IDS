"""
Data preprocessing service for supervised ML classification
Handles data cleaning, feature engineering, and data splitting
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Data preprocessing service for ML classification
    """
    
    def __init__(self, config=None):
        """
        Initialize data preprocessor
        
        Args:
            config: Configuration object (optional)
        """
        # Use RobustScaler for better outlier resistance
        self.scaler = RobustScaler()
        self.feature_names = None  # Will be set dynamically from data
        self.config = config
        self.use_robust_scaler = getattr(config, 'USE_ROBUST_SCALER', True) if config else True
        if not self.use_robust_scaler:
            self.scaler = StandardScaler()
        logger.info(f"DataPreprocessor initialized (scaler: {'RobustScaler' if self.use_robust_scaler else 'StandardScaler'})")
    
    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get feature column names (exclude label and metadata columns)"""
        exclude_cols = ['label', 'source_ip', 'dest_ip', 'protocol', 'dst_port', 
                       'timestamp', 'labeled_by', 'confidence', 'metadata', '_id']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Update feature_names if not set or different
        if self.feature_names is None or set(self.feature_names) != set(feature_cols):
            self.feature_names = feature_cols
            logger.info(f"Detected {len(feature_cols)} features")
        
        return feature_cols
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean training data (handles 80+ features)
        
        Args:
            df: DataFrame with features and labels
            
        Returns:
            Cleaned DataFrame
        """
        try:
            df_clean = df.copy()
            
            # Get feature columns dynamically
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
            
            # Remove constant features (zero variance)
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
            # For numeric features, fill with median
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
                    logger.debug(f"Filled missing values in {feature} with median: {median_value}")
            
            # For non-numeric features, fill with mode or empty string
            for feature in feature_cols:
                if feature in df_clean.columns and feature not in numeric_features:
                    if df_clean[feature].isna().any():
                        mode_value = df_clean[feature].mode()
                        fill_value = mode_value[0] if len(mode_value) > 0 else ''
                        df_clean[feature].fillna(fill_value, inplace=True)
            
            # Remove rows with missing labels
            if 'label' in df_clean.columns:
                before_count = len(df_clean)
                df_clean = df_clean.dropna(subset=['label'])
                removed = before_count - len(df_clean)
                if removed > 0:
                    logger.info(f"Removed {removed} samples with missing labels")
            
            # Handle outliers using IQR method (cap extreme values) - only for numeric features
            # Use 2.5 IQR instead of 3 for less aggressive capping (preserve more data)
            for feature in numeric_features:
                if feature in df_clean.columns:
                    Q1 = df_clean[feature].quantile(0.25)
                    Q3 = df_clean[feature].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    if IQR > 0:  # Only cap if there's variance
                        lower_bound = Q1 - 2.5 * IQR  # 2.5 IQR for less aggressive capping
                        upper_bound = Q3 + 2.5 * IQR
                        
                        outliers_count = ((df_clean[feature] < lower_bound) | 
                                         (df_clean[feature] > upper_bound)).sum()
                        if outliers_count > 0:
                            df_clean[feature] = df_clean[feature].clip(lower=lower_bound, upper=upper_bound)
                            logger.debug(f"Capped {outliers_count} outliers in {feature}")
            
            return df_clean
            
        except Exception as e:
            logger.error(f"Error cleaning data: {e}")
            return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create derived features with advanced feature engineering
        
        Args:
            df: DataFrame with base features
            
        Returns:
            DataFrame with additional engineered features
        """
        try:
            df_eng = df.copy()
            
            # Get feature columns (exclude label and metadata)
            feature_cols = self._get_feature_columns(df_eng)
            
            # Ratio features
            if 'packet_size' in df_eng.columns and 'connection_duration' in df_eng.columns:
                # Packet size per second
                df_eng['packet_size_per_second'] = np.where(
                    df_eng['connection_duration'] > 0,
                    df_eng['packet_size'] / (df_eng['connection_duration'] + 1e-6),
                    0
                )
            
            if 'failed_login_attempts' in df_eng.columns and 'access_frequency' in df_eng.columns:
                # Failed login ratio
                df_eng['failed_login_ratio'] = np.where(
                    df_eng['access_frequency'] > 0,
                    df_eng['failed_login_attempts'] / (df_eng['access_frequency'] + 1e-6),
                    0
                )
            
            if 'data_transfer_rate' in df_eng.columns and 'packet_size' in df_eng.columns:
                # Transfer efficiency
                df_eng['transfer_efficiency'] = np.where(
                    df_eng['packet_size'] > 0,
                    df_eng['data_transfer_rate'] / (df_eng['packet_size'] + 1e-6),
                    0
                )
            
            # Interaction features (multiplication of key pairs)
            key_features = ['packet_size', 'connection_duration', 'data_transfer_rate', 
                          'access_frequency', 'failed_login_attempts']
            available_key_features = [f for f in key_features if f in df_eng.columns]
            
            if len(available_key_features) >= 2:
                # Create interaction features for top pairs
                for i, feat1 in enumerate(available_key_features[:3]):  # Limit to avoid explosion
                    for feat2 in available_key_features[i+1:min(i+3, len(available_key_features))]:
                        if feat1 in df_eng.columns and feat2 in df_eng.columns:
                            interaction_name = f'{feat1}_x_{feat2}'
                            if interaction_name not in df_eng.columns:
                                df_eng[interaction_name] = df_eng[feat1] * df_eng[feat2]
            
            # Polynomial features for key metrics (squared terms)
            for feat in ['packet_size', 'connection_duration', 'data_transfer_rate']:
                if feat in df_eng.columns:
                    squared_name = f'{feat}_squared'
                    if squared_name not in df_eng.columns:
                        df_eng[squared_name] = df_eng[feat] ** 2
            
            # Time-based features (if timestamp exists)
            if 'timestamp' in df_eng.columns:
                try:
                    df_eng['timestamp'] = pd.to_datetime(df_eng['timestamp'], errors='coerce')
                    df_eng['hour_of_day'] = df_eng['timestamp'].dt.hour
                    df_eng['day_of_week'] = df_eng['timestamp'].dt.dayofweek
                    df_eng['is_weekend'] = (df_eng['day_of_week'] >= 5).astype(int)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug(f"Could not extract time-based features from timestamp: {e}")
            
            # Log transformation for highly skewed features (if they exist)
            skewed_features = ['packet_size', 'data_transfer_rate', 'connection_duration']
            for feat in skewed_features:
                if feat in df_eng.columns:
                    # Only apply log if values are positive
                    if (df_eng[feat] > 0).any():
                        log_name = f'{feat}_log'
                        if log_name not in df_eng.columns:
                            df_eng[log_name] = np.log1p(df_eng[feat].clip(lower=0))
            
            logger.info(f"Feature engineering completed. Total features: {len(self._get_feature_columns(df_eng))}")
            return df_eng
            
        except Exception as e:
            logger.error(f"Error engineering features: {e}")
            return df
    
    def normalize_features(self, X_train: np.ndarray, X_test: Optional[np.ndarray] = None,
                          method: str = 'standard') -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Normalize/standardize features
        
        Args:
            X_train: Training features
            X_test: Test features (optional)
            method: Normalization method ('standard' or 'robust')
            
        Returns:
            Tuple of (normalized X_train, normalized X_test)
        """
        try:
            if method == 'robust':
                scaler = RobustScaler()
            else:
                scaler = StandardScaler()
            
            X_train_scaled = scaler.fit_transform(X_train)
            self.scaler = scaler  # Store for later use
            
            if X_test is not None:
                X_test_scaled = scaler.transform(X_test)
                return X_train_scaled, X_test_scaled
            
            return X_train_scaled, None
            
        except Exception as e:
            logger.error(f"Error normalizing features: {e}")
            return X_train, X_test
    
    def split_data(self, df: pd.DataFrame, test_size: float = 0.15,
                  val_size: float = 0.15, stratify: bool = True,
                  random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split data into train, validation, and test sets
        
        Args:
            df: DataFrame with features and labels
            test_size: Proportion of test set
            val_size: Proportion of validation set
            stratify: Whether to maintain class balance
            random_state: Random seed
            
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        try:
            if 'label' not in df.columns:
                raise ValueError("DataFrame must contain 'label' column")
            
            # First split: train+val vs test
            stratify_col = df['label'] if stratify else None
            
            train_val_df, test_df = train_test_split(
                df,
                test_size=test_size,
                stratify=stratify_col,
                random_state=random_state
            )
            
            # Second split: train vs val
            # Adjust val_size relative to train+val set
            adjusted_val_size = val_size / (1 - test_size)
            stratify_col = train_val_df['label'] if stratify else None
            
            train_df, val_df = train_test_split(
                train_val_df,
                test_size=adjusted_val_size,
                stratify=stratify_col,
                random_state=random_state
            )
            
            logger.info(f"Data split: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")
            
            return train_df, val_df, test_df
            
        except Exception as e:
            logger.error(f"Error splitting data: {e}")
            raise
    
    def select_features(self, X: np.ndarray, y: np.ndarray, k: int = 'all',
                       method: str = 'f_classif') -> Tuple[np.ndarray, Any]:
        """
        Select best features using statistical tests
        
        Args:
            X: Feature matrix
            y: Target labels
            k: Number of features to select ('all' for all features)
            method: Feature selection method ('f_classif' or 'mutual_info')
            
        Returns:
            Tuple of (selected features, selector object)
        """
        try:
            if k == 'all':
                k = X.shape[1]
            
            if method == 'mutual_info':
                selector = SelectKBest(score_func=mutual_info_classif, k=k)
            else:
                selector = SelectKBest(score_func=f_classif, k=k)
            
            X_selected = selector.fit_transform(X, y)
            
            logger.info(f"Selected {k} features using {method}")
            return X_selected, selector
            
        except Exception as e:
            logger.error(f"Error selecting features: {e}")
            return X, None
    
    def select_features_comprehensive(self, df: pd.DataFrame, target_col: str = 'label',
                                     max_features: int = 60, 
                                     use_rf_importance: bool = True) -> pd.DataFrame:
        """
        Comprehensive feature selection: removes low-importance, highly correlated, 
        and constant features to reduce to top N features
        
        Args:
            df: DataFrame with features and labels
            target_col: Name of target column
            max_features: Maximum number of features to keep
            use_rf_importance: Whether to use Random Forest importance for selection
            
        Returns:
            DataFrame with selected features
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            
            df_selected = df.copy()
            feature_cols = self._get_feature_columns(df_selected)
            
            logger.info(f"Starting feature selection from {len(feature_cols)} features...")
            
            # Step 1: Remove constant/near-constant features
            constant_features = []
            for col in feature_cols:
                if col in df_selected.columns:
                    if df_selected[col].nunique() <= 1:
                        constant_features.append(col)
                    elif df_selected[col].var() < 0.01:  # Near-constant (variance < 0.01)
                        constant_features.append(col)
            
            if constant_features:
                logger.info(f"Removing {len(constant_features)} constant/near-constant features")
                df_selected = df_selected.drop(columns=constant_features)
                feature_cols = [f for f in feature_cols if f not in constant_features]
            
            # Step 2: Remove highly correlated features
            if len(feature_cols) > 1:
                numeric_cols = [col for col in feature_cols if col in df_selected.columns 
                               and pd.api.types.is_numeric_dtype(df_selected[col])]
                
                if len(numeric_cols) > 1:
                    corr_matrix = df_selected[numeric_cols].corr().abs()
                    upper_triangle = corr_matrix.where(
                        np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
                    )
                    
                    # Find pairs with correlation > 0.95
                    high_corr_pairs = []
                    for col in upper_triangle.columns:
                        high_corr = upper_triangle.index[upper_triangle[col] > 0.95].tolist()
                        for corr_col in high_corr:
                            high_corr_pairs.append((col, corr_col))
                    
                    # Remove one feature from each highly correlated pair
                    features_to_remove = set()
                    for feat1, feat2 in high_corr_pairs:
                        # Keep the feature with higher variance (more informative)
                        if feat1 in df_selected.columns and feat2 in df_selected.columns:
                            var1 = df_selected[feat1].var()
                            var2 = df_selected[feat2].var()
                            if var1 < var2:
                                features_to_remove.add(feat1)
                            else:
                                features_to_remove.add(feat2)
                    
                    if features_to_remove:
                        logger.info(f"Removing {len(features_to_remove)} highly correlated features")
                        df_selected = df_selected.drop(columns=list(features_to_remove))
                        feature_cols = [f for f in feature_cols if f not in features_to_remove]
            
            # Step 3: Use Random Forest importance or mutual information to select top features
            if len(feature_cols) > max_features:
                X = df_selected[feature_cols].values
                y = df_selected[target_col].map({'benign': 0, 'malicious': 1}).values
                
                # Handle NaN values
                X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
                
                if use_rf_importance:
                    # Use Random Forest feature importance
                    logger.info("Using Random Forest feature importance for selection...")
                    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
                    rf.fit(X, y)
                    importances = rf.feature_importances_
                    
                    # Get top N features
                    top_indices = np.argsort(importances)[-max_features:]
                    selected_features = [feature_cols[i] for i in top_indices]
                else:
                    # Use mutual information
                    logger.info("Using mutual information for selection...")
                    mi_scores = mutual_info_classif(X, y, random_state=42)
                    top_indices = np.argsort(mi_scores)[-max_features:]
                    selected_features = [feature_cols[i] for i in top_indices]
                
                # Keep only selected features plus label and metadata
                keep_cols = selected_features + [target_col]
                metadata_cols = ['source_ip', 'dest_ip', 'protocol', 'dst_port', 
                               'timestamp', 'labeled_by', 'confidence', 'metadata', '_id']
                keep_cols.extend([col for col in metadata_cols if col in df_selected.columns])
                
                df_selected = df_selected[keep_cols]
                logger.info(f"Selected top {len(selected_features)} features using {'RF importance' if use_rf_importance else 'mutual information'}")
            else:
                logger.info(f"Feature count ({len(feature_cols)}) already <= max_features ({max_features})")
            
            # Update feature_names
            self.feature_names = self._get_feature_columns(df_selected)
            logger.info(f"Final feature count: {len(self.feature_names)}")
            
            return df_selected
            
        except Exception as e:
            logger.error(f"Error in comprehensive feature selection: {e}")
            return df
    
    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare feature matrix from DataFrame (handles 80+ features)

        Args:
            df: DataFrame with features

        Returns:
            Feature matrix as numpy array
        """
        try:
            # Get feature columns dynamically
            feature_cols = self._get_feature_columns(df)
            
            if not feature_cols:
                raise ValueError("No feature columns found in DataFrame")
            
            # Select only numeric feature columns (convert non-numeric if needed)
            numeric_cols = []
            for col in feature_cols:
                if col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        numeric_cols.append(col)
                    else:
                        # Try to convert to numeric
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            numeric_cols.append(col)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Skipping non-numeric feature {col}: {e}")
            
            if not numeric_cols:
                raise ValueError("No numeric feature columns found")
            
            X = df[numeric_cols].values

            # Handle any remaining NaN values
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

            return X

        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            raise
    
    def prepare_labels(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare label array from DataFrame
        
        Args:
            df: DataFrame with labels
            
        Returns:
            Label array (0 for benign, 1 for malicious)
        """
        try:
            if 'label' not in df.columns:
                raise ValueError("DataFrame must contain 'label' column")
            
            # Map labels to binary: benign=0, malicious=1
            y = df['label'].map({'benign': 0, 'malicious': 1}).values
            
            return y
            
        except Exception as e:
            logger.error(f"Error preparing labels: {e}")
            raise
    
    def get_feature_importance(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Calculate feature importance scores
        
        Args:
            X: Feature matrix
            y: Target labels
            
        Returns:
            Dictionary mapping feature names to importance scores
        """
        try:
            # Use mutual information for feature importance
            scores = mutual_info_classif(X, y, random_state=42)
            
            importance_dict = {}
            for i, feature_name in enumerate(self.feature_names[:len(scores)]):
                importance_dict[feature_name] = float(scores[i])
            
            # Sort by importance
            importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            
            return importance_dict
            
        except Exception as e:
            logger.error(f"Error calculating feature importance: {e}")
            return {}
    
    def analyze_correlations(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze feature correlations
        
        Args:
            df: DataFrame with features
            
        Returns:
            Correlation matrix
        """
        try:
            feature_cols = [col for col in self.feature_names if col in df.columns]
            if not feature_cols:
                return pd.DataFrame()
            
            corr_matrix = df[feature_cols].corr()
            return corr_matrix
            
        except Exception as e:
            logger.error(f"Error analyzing correlations: {e}")
            return pd.DataFrame()