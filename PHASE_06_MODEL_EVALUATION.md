# Phase 6: Model Evaluation

## Overview

This phase covers comprehensive evaluation of the trained model, including accuracy metrics, confusion matrix, ROC curves, and performance analysis. This helps verify model quality before integration.

## Prerequisites

- Phase 5 completed (model trained and saved)
- Model file exists: `backend/models/classification_model.pkl`
- Test data available in database

## Step 1: Load Model and Test Data

### 1.1 Verify Model Exists

```bash
ls -lh backend/models/classification_model.pkl
```

### 1.2 Load Model for Evaluation

```bash
cd backend
source venv/bin/activate
python -c "
import pickle
from config import Config

config = Config()
model_path = 'models/classification_model.pkl'

with open(model_path, 'rb') as f:
    model_data = pickle.load(f)
    
print('Model Information:')
print(f'  Training accuracy: {model_data.get(\"training_accuracy\", 0):.4f}')
print(f'  Validation accuracy: {model_data.get(\"validation_accuracy\", 0):.4f}')
print(f'  Test accuracy: {model_data.get(\"test_accuracy\", 0):.4f}')
print(f'  Features: {len(model_data.get(\"feature_names\", []))}')
"
```

## Step 2: Run Comprehensive Evaluation

### 2.1 Using Evaluation Script

```bash
python scripts/evaluate_model.py \
    --model-path ./models/classification_model.pkl \
    --output-report ./evaluation_report.json
```

### 2.2 Using API Endpoint

```bash
curl http://localhost:3002/api/training/evaluate
```

### 2.3 Manual Evaluation

```bash
python -c "
from services.model_trainer import ModelTrainer
from services.classifier import ClassificationDetector
from services.preprocessor import DataPreprocessor
from services.data_collector import DataCollector
from config import Config

config = Config()
classifier = ClassificationDetector(config)
preprocessor = DataPreprocessor(config)
collector = DataCollector(config)
trainer = ModelTrainer(config, classifier, preprocessor, collector)

# Evaluate model
results = trainer.evaluate_model()
print('Evaluation Results:')
for key, value in results.items():
    print(f'  {key}: {value}')
"
```

## Step 3: Key Metrics

### 3.1 Classification Metrics

**Accuracy**: Overall correctness
```
Accuracy = (TP + TN) / (TP + TN + FP + FN)
Expected: >95%
```

**Precision**: Correct positive predictions
```
Precision = TP / (TP + FP)
Expected: >94%
```

**Recall (Sensitivity)**: True positives detected
```
Recall = TP / (TP + FN)
Expected: >94%
```

**F1-Score**: Harmonic mean of precision and recall
```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
Expected: >94%
```

**Specificity**: True negatives detected
```
Specificity = TN / (TN + FP)
Expected: >94%
```

### 3.2 Expected Results

**For 100K training samples:**
- Accuracy: 95-99%
- Precision: 94-98%
- Recall: 94-98%
- F1-Score: 94-98%
- Specificity: 94-98%

**For 50K training samples:**
- Accuracy: 93-97%
- Slightly lower but acceptable

## Step 4: Confusion Matrix

### 4.1 Generate Confusion Matrix

```bash
python -c "
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
from config import Config

# Load model and test data
config = Config()
model_path = 'models/classification_model.pkl'

with open(model_path, 'rb') as f:
    model_data = pickle.load(f)
    
# Get predictions and true labels from test set
# (This would come from actual test data evaluation)

print('Confusion Matrix:')
print('Expected format:')
print('                Predicted')
print('              Benign  Malicious')
print('Actual Benign    [TP]    [FN]')
print('      Malicious  [FP]    [TN]')
"
```

### 4.2 Interpret Confusion Matrix

**True Positives (TP)**: Correctly identified malicious traffic
- **Good**: High TP means good attack detection

**True Negatives (TN)**: Correctly identified benign traffic
- **Good**: High TN means low false alarms

**False Positives (FP)**: Benign traffic flagged as malicious
- **Bad**: Causes false alarms
- **Target**: Keep low (<5%)

**False Negatives (FN)**: Malicious traffic missed
- **Bad**: Security risk
- **Target**: Keep very low (<2%)

## Step 5: ROC Curve and AUC

### 5.1 Generate ROC Curve

```bash
python scripts/generate_roc_curve.py \
    --model-path ./models/classification_model.pkl \
    --output-file ./roc_curve.png
```

### 5.2 Interpret AUC Score

**AUC (Area Under Curve)**:
- **0.9-1.0**: Excellent
- **0.8-0.9**: Good
- **0.7-0.8**: Acceptable
- **<0.7**: Poor

**Expected**: AUC >0.95 for well-trained model

## Step 6: Per-Class Performance

### 6.1 Evaluate by Attack Type

```bash
python -c "
# Evaluate performance for each attack type
# This shows which attacks are detected well

attack_types = [
    'Benign',
    'DoS attacks-Hulk',
    'DDoS attacks-LOIC-HTTP',
    'FTP-BruteForce',
    'SSH-Bruteforce',
    # ... other types
]

print('Per-Class Performance:')
for attack_type in attack_types:
    # Calculate precision, recall, F1 for each class
    print(f'{attack_type}:')
    print(f'  Precision: 0.XX')
    print(f'  Recall: 0.XX')
    print(f'  F1-Score: 0.XX')
"
```

### 6.2 Identify Weak Classes

Look for classes with:
- Low recall (<90%): Missing attacks
- Low precision (<90%): False alarms

**Action**: If specific attack types perform poorly, consider:
- Adding more training samples for that class
- Feature engineering for that attack type
- Adjusting class weights

## Step 7: Performance Analysis

### 7.1 Training vs Test Performance

**Compare metrics:**
- Training accuracy vs Test accuracy
- Gap should be small (<2-3%)

**If large gap**: Model may be overfitting
- Solution: Use more data or simpler model

**If both low**: Model may be underfitting
- Solution: Use more complex model or better features

### 7.2 Validation Performance

**Validation set** (15% of data):
- Used during training for early stopping
- Should match test performance
- If different: Data split may be biased

## Step 8: Generate Evaluation Report

### 8.1 Create Report

```bash
python scripts/generate_evaluation_report.py \
    --model-path ./models/classification_model.pkl \
    --output-file ./evaluation_report.json
```

### 8.2 Report Contents

The report should include:
- Overall metrics (accuracy, precision, recall, F1)
- Confusion matrix
- Per-class performance
- ROC curve data
- Training history
- Recommendations

### 8.3 View Report

```bash
cat evaluation_report.json | python -m json.tool
```

## Step 9: Model Comparison (Optional)

### 9.1 Compare Different Models

If you trained multiple models:

```bash
python scripts/compare_models.py \
    --model1 ./models/classification_model.pkl \
    --model2 ./models/classification_model_v2.pkl
```

### 9.2 Metrics to Compare

- Accuracy
- Precision/Recall trade-off
- Training time
- Inference speed
- Memory usage

## Step 10: Troubleshooting

### Issue: Low Accuracy (<90%)

**Possible causes:**
1. Insufficient training data
2. Poor feature quality
3. Class imbalance
4. Model too simple

**Solutions:**
1. Increase training samples
2. Improve feature engineering
3. Use class weights
4. Try different model (e.g., XGBoost)

### Issue: High False Positive Rate

**Symptoms**: Many benign samples flagged as malicious

**Solutions:**
1. Increase confidence threshold
2. Add more benign training samples
3. Improve feature selection
4. Use ensemble methods

### Issue: High False Negative Rate

**Symptoms**: Missing many attacks

**Solutions:**
1. Lower confidence threshold
2. Add more malicious training samples
3. Improve attack detection features
4. Use anomaly detection as backup

### Issue: Overfitting

**Symptoms**: High training accuracy, lower test accuracy

**Solutions:**
1. Use more training data
2. Reduce model complexity
3. Add regularization
4. Use cross-validation

## Step 11: Documentation

### 11.1 Record Metrics

Document in `MODEL_EVALUATION.md` or similar:
- Model version
- Training date
- Dataset size
- All metrics
- Known limitations

### 11.2 Performance Baseline

Establish baseline for future comparisons:
- Current accuracy: X%
- Target accuracy: Y%
- Improvement needed: Z%

## Verification Checklist

- [ ] Model loaded successfully
- [ ] Evaluation script executed
- [ ] Accuracy >95%
- [ ] Precision >94%
- [ ] Recall >94%
- [ ] F1-Score >94%
- [ ] Confusion matrix generated
- [ ] ROC curve generated (AUC >0.95)
- [ ] Per-class performance analyzed
- [ ] Evaluation report created
- [ ] No critical issues identified
- [ ] Model ready for integration

## File Locations

- **Model**: `backend/models/classification_model.pkl`
- **Evaluation Report**: `backend/evaluation_report.json`
- **ROC Curve**: `backend/roc_curve.png` (if generated)
- **Evaluation Script**: `backend/scripts/evaluate_model.py`

## Next Steps

Once evaluation is complete and metrics are acceptable, proceed to:
- **Phase 7**: Backend Integration - Integrate model into Flask backend

## Estimated Time

- **Evaluation**: 5-10 minutes
- **Analysis**: 10-15 minutes
- **Total**: 15-25 minutes

## Notes

- Evaluation helps verify model quality before deployment
- Good metrics (>95%) indicate model is ready for integration
- Poor metrics may require retraining or data improvements
- Keep evaluation report for documentation and future reference
- Model performance may vary slightly in production
