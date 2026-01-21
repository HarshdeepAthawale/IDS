# Dataset and Training Documentation

## Overview

This project uses the **CICIDS2018** dataset for training a supervised machine learning model to classify network traffic as either **benign** or **malicious**. The training pipeline includes advanced feature engineering, feature selection, class imbalance handling, and hyperparameter tuning to achieve high accuracy.

---

## Dataset: CICIDS2018

### Dataset Information

- **Name**: CICIDS2018 (Canadian Institute for Cybersecurity Intrusion Detection System Dataset 2018)
- **Source**: University of New Brunswick, Canadian Institute for Cybersecurity
- **Purpose**: Network intrusion detection and classification
- **Format**: Preprocessed JSON file containing labeled network traffic samples

### Dataset Statistics

- **Total Samples**: 50,000 samples
- **Class Distribution**:
  - **Benign**: 30,000 samples (60%)
  - **Malicious**: 20,000 samples (40%)
- **File Location**: `backend/data/cicids2018_preprocessed_50k.json`
- **File Size**: ~122 MB

### Data Format

Each sample in the dataset contains:
- **Features**: 70+ network traffic features including:
  - Packet size and duration
  - Connection statistics
  - Protocol information
  - Data transfer rates
  - Access frequency
  - Failed login attempts
  - And more...
- **Label**: `"benign"` or `"malicious"`

### Data Loading

The training pipeline loads data from the preprocessed JSON file to avoid MongoDB SSL compatibility issues with Python 3.14:

```python
# Location: backend/services/model_trainer.py
# Method: load_training_data()
# - Loads all 50K samples from JSON file
# - Validates 60:40 class ratio
# - Performs data quality checks
# - Removes duplicates and samples with >50% missing values
```

---

## Training Pipeline

### Overview

The training process follows a comprehensive pipeline designed to maximize model accuracy:

1. **Data Loading & Validation**
2. **Data Cleaning**
3. **Feature Engineering**
4. **Feature Selection**
5. **Data Splitting**
6. **Class Imbalance Handling (SMOTE)**
7. **Hyperparameter Tuning**
8. **Model Training**
9. **Evaluation & Validation**

### Step-by-Step Process

#### 1. Data Loading & Validation

- Loads 50,000 samples from JSON file
- Validates class distribution (30K benign, 20K malicious)
- Performs data quality checks:
  - Removes samples with >50% missing values
  - Removes duplicate samples
  - Validates 60:40 class ratio

**Output**: ~47,974 clean samples (after removing duplicates)

#### 2. Data Cleaning

- Removes constant/near-constant features (variance < 0.01)
- Handles missing values (median imputation for numeric features)
- Caps outliers using IQR method (2.5 IQR threshold)
- Removes rows with missing labels

**Result**: Clean dataset ready for feature engineering

#### 3. Feature Engineering

Creates advanced features to improve model performance:

- **Ratio Features**:
  - `packet_size_per_second`
  - `failed_login_ratio`
  - `transfer_efficiency`

- **Interaction Features**:
  - Multiplications of key feature pairs
  - Example: `packet_size × connection_duration`

- **Polynomial Features**:
  - Squared terms for key metrics
  - Example: `packet_size_squared`

- **Time-based Features** (if timestamp available):
  - `hour_of_day`
  - `day_of_week`
  - `is_weekend`

- **Log Transformations**:
  - Applied to highly skewed features
  - Example: `packet_size_log`

**Result**: 70 engineered features

#### 4. Feature Selection

Reduces feature count to top 50-60 most important features:

- **Removes constant/near-constant features**
- **Removes highly correlated features** (correlation > 0.95)
- **Uses Random Forest feature importance** to select top features
- **Target**: 50-60 features (configurable via `MAX_FEATURES`)

**Result**: ~39-60 selected features (reduces noise, improves performance)

#### 5. Data Splitting

Splits data into train/validation/test sets:

- **Training Set**: 70% (~26,385 samples)
- **Validation Set**: 15% (~7,196 samples)
- **Test Set**: 15% (~14,393 samples)
- **Stratified**: Maintains class balance across splits

#### 6. Class Imbalance Handling (SMOTE)

Applies SMOTE (Synthetic Minority Oversampling Technique) to balance classes:

- **Before SMOTE**: 15,834 benign, 10,551 malicious
- **After SMOTE**: Balanced to majority class size
- **Applied only to training set** (not validation/test)
- **Purpose**: Improves recall for malicious detection

**Note**: SMOTE is enabled by default (`USE_SMOTE=true`)

#### 7. Hyperparameter Tuning

Performs RandomizedSearchCV to find optimal hyperparameters:

- **Method**: RandomizedSearchCV
- **Iterations**: 50 (configurable via `HYPERPARAMETER_TUNING_N_ITER`)
- **CV Folds**: 5 (configurable via `HYPERPARAMETER_TUNING_CV`)
- **Optimization Target**: F1-score (balances precision and recall)

**Search Space for Random Forest**:
```python
{
    'n_estimators': [200, 300, 500, 700, 1000],
    'max_depth': [15, 20, 25, 30, None],
    'min_samples_split': [2, 5, 10, 20],
    'min_samples_leaf': [1, 2, 4, 8],
    'max_features': ['sqrt', 'log2', 0.5, 0.7, None],
    'bootstrap': [True, False],
    'max_samples': [0.8, 0.9, 1.0]
}
```

**Time**: ~1-2 hours for 50 iterations × 5-fold CV

#### 8. Model Training

Trains the final model with optimal hyperparameters:

- **Model Type**: Random Forest Classifier (default)
- **Class Weights**: Custom weights favoring malicious detection `{0: 0.4, 1: 0.6}`
- **Features**: Uses selected features from step 4
- **Scaler**: RobustScaler (better outlier resistance)

#### 9. Evaluation & Validation

Comprehensive evaluation on test set:

- **5-Fold Cross-Validation**: Robust performance estimate
- **Test Set Evaluation**: Final performance metrics
- **Metrics Calculated**:
  - Accuracy
  - Precision
  - Recall
  - F1-Score
  - ROC-AUC
  - PR-AUC
  - Confusion Matrix

**Success Criteria**:
- Accuracy >= 90%
- Precision >= 85%
- Recall >= 85% (critical for IDS)
- F1-Score >= 87%
- ROC-AUC >= 0.95

---

## Configuration

### Environment Variables

Key configuration options in `.env` file:

```env
# Dataset Settings
MAX_TRAINING_SAMPLES=50000

# Feature Selection
MAX_FEATURES=60
USE_ROBUST_SCALER=true

# Class Imbalance
USE_SMOTE=true

# Hyperparameter Tuning
HYPERPARAMETER_TUNING_N_ITER=50
HYPERPARAMETER_TUNING_CV=5

# Model Settings
CLASSIFICATION_MODEL_TYPE=random_forest
TRAIN_TEST_SPLIT_RATIO=0.7
```

---

## Running Training

### Command

```bash
cd backend
source venv/bin/activate
python scripts/train_from_cicids2018.py --hyperparameter-tuning
```

### Options

- `--hyperparameter-tuning`: Enable hyperparameter tuning (recommended)
- `--no-hyperparameter-tuning`: Skip tuning (faster, lower accuracy)

### Expected Output

Training will output:
1. Data loading progress
2. Feature engineering summary
3. Feature selection results
4. SMOTE application status
5. Hyperparameter tuning progress
6. Final model metrics
7. Success criteria check

### Training Time

- **Without Hyperparameter Tuning**: ~2-5 minutes
- **With Hyperparameter Tuning**: ~1-2 hours (50 iterations × 5-fold CV)

---

## Model Output

### Saved Files

- **Model File**: `backend/classification_model.pkl`
  - Contains trained model, scaler, feature names, and metadata
  - Size: ~4-5 MB

- **Evaluation Results**: `backend/evaluation_results/`
  - JSON reports with detailed metrics
  - Text summaries
  - Confusion matrices
  - ROC/PR curves

### Model Metadata

The saved model includes:
- Model type and hyperparameters
- Feature names (for inference)
- Optimal threshold (tuned for recall)
- Training timestamp
- Performance metrics

---

## Key Improvements Implemented

### 1. Data Quality
- ✅ Full 50K samples loaded and validated
- ✅ Data quality checks (missing values, duplicates)
- ✅ Class ratio validation (60:40)

### 2. Feature Engineering
- ✅ Advanced feature creation (interactions, polynomials)
- ✅ Time-based features
- ✅ Log transformations for skewed data

### 3. Feature Selection
- ✅ Removes noise (constant, correlated features)
- ✅ Selects top 50-60 features using RF importance
- ✅ Reduces overfitting risk

### 4. Class Imbalance
- ✅ SMOTE for oversampling minority class
- ✅ Custom class weights favoring malicious detection
- ✅ Threshold tuning for optimal recall

### 5. Hyperparameter Optimization
- ✅ Expanded search space (7 parameters)
- ✅ 50 iterations with 5-fold CV
- ✅ F1-score optimization with recall bias

### 6. Evaluation
- ✅ 5-fold cross-validation
- ✅ Comprehensive metrics
- ✅ Success criteria validation

---

## Model Performance

### Current Performance (After Improvements)

**Baseline** (before improvements):
- Accuracy: 65.44%
- Precision: 58.34%
- Recall: 47.53%
- F1-Score: 52.38%
- ROC-AUC: 0.68

**Target Performance** (with all improvements):
- Accuracy: 90%+
- Precision: 85%+
- Recall: 85%+ (critical for IDS)
- F1-Score: 87%+
- ROC-AUC: 0.95+

### Expected Improvements

- **Data Fix** (26K → 50K samples): +5-8% accuracy
- **Feature Selection**: +5-10% accuracy
- **SMOTE**: +8-12% recall improvement
- **Hyperparameter Tuning**: +3-7% accuracy
- **Combined**: 85-92% accuracy target

---

## Usage in Production

### Loading the Model

```python
from services.classifier import ClassificationDetector
from config import Config

config = Config()
classifier = ClassificationDetector(config)

# Model is automatically loaded from classification_model.pkl
if classifier.is_trained:
    # Classify new samples
    result = classifier.classify(features_dict)
    print(f"Label: {result['label']}, Confidence: {result['confidence']}")
```

### Real-time Classification

The model is integrated into the IDS backend and automatically classifies network traffic in real-time:

1. **Packet Capture** → Feature Extraction
2. **Feature Extraction** → Classification
3. **Classification** → Alert Generation (if malicious)

---

## Troubleshooting

### Common Issues

1. **SSL Errors with MongoDB**
   - **Solution**: Training uses JSON file, MongoDB connection is optional
   - SSL errors are suppressed and don't affect training

2. **SMOTE Fails**
   - **Solution**: Training continues without SMOTE
   - Check class distribution in logs

3. **Low Accuracy**
   - **Solution**: Ensure hyperparameter tuning is enabled
   - Check feature selection results
   - Verify all 50K samples are loaded

4. **Training Takes Too Long**
   - **Solution**: Reduce `HYPERPARAMETER_TUNING_N_ITER` (e.g., 20 instead of 50)
   - Reduce CV folds (e.g., 3 instead of 5)

---

## References

- **CICIDS2018 Dataset**: [Canadian Institute for Cybersecurity](https://www.unb.ca/cic/datasets/ids-2018.html)
- **SMOTE**: Synthetic Minority Oversampling Technique
- **Random Forest**: Ensemble learning algorithm
- **RobustScaler**: Outlier-resistant feature scaling

---

## Summary

This project uses the CICIDS2018 dataset (50K samples) to train a Random Forest classifier for network intrusion detection. The training pipeline includes:

- ✅ Advanced feature engineering
- ✅ Intelligent feature selection
- ✅ Class imbalance handling (SMOTE)
- ✅ Comprehensive hyperparameter tuning
- ✅ Robust evaluation with cross-validation

The goal is to achieve **90%+ accuracy** with **85%+ recall** to effectively detect malicious network traffic while minimizing false negatives.
