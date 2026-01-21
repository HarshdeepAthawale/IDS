# Phase 5: Model Training

## Overview

This phase covers training a Random Forest classifier on the imported subset data (50K samples). The training is optimized for local execution on i5 12th gen with 16GB RAM, with expected training time of 5-10 minutes.

## Prerequisites

- Phase 4 completed (data imported to database)
- Database contains 50,000 labeled samples (30K benign, 20K malicious)
- Environment configured with `MAX_TRAINING_SAMPLES=50000`

## Step 1: Verify Training Configuration

### 1.1 Check Environment Variables

```bash
cd backend
cat .env | grep -E "TRAINING|CLASSIFICATION|MAX_TRAINING"
```

**Expected configuration:**
```bash
CLASSIFICATION_ENABLED=true
CLASSIFICATION_MODEL_TYPE=random_forest
MAX_TRAINING_SAMPLES=50000
BATCH_LOADING_ENABLED=true
HYPERPARAMETER_TUNING_ENABLED=false
TRAIN_TEST_SPLIT_RATIO=0.7
```

### 1.2 Verify Database Has Training Data

```bash
source venv/bin/activate
python -c "
from config import Config
from services.data_collector import DataCollector

config = Config()
collector = DataCollector(config)
stats = collector.get_statistics()

print(f'Total samples: {stats.get(\"total_samples\", 0):,}')
print(f'Labeled samples: {stats.get(\"labeled_samples\", 0):,}')
print(f'Benign: {stats.get(\"benign_count\", 0):,}')
print(f'Malicious: {stats.get(\"malicious_count\", 0):,}')

if stats.get('labeled_samples', 0) < 1000:
    print('WARNING: Not enough training data!')
else:
    print('✓ Sufficient training data available')
"
```

**Expected**: Exactly 50,000 labeled samples (30,000 benign, 20,000 malicious)

## Step 2: Training Options

### Option A: Training Script (Recommended)

```bash
cd backend
source venv/bin/activate
python scripts/train_from_cicids2018.py
```

### Option B: API Endpoint

```bash
curl -X POST http://localhost:3002/api/training/train \
    -H "Content-Type: application/json" \
    -d '{"hyperparameter_tuning": false}'
```

### Option C: Python Direct

```bash
cd backend
source venv/bin/activate
python -c "
from config import Config
from services.classifier import ClassificationDetector
from services.preprocessor import DataPreprocessor
from services.model_trainer import ModelTrainer
from services.data_collector import DataCollector

config = Config()
classifier = ClassificationDetector(config)
preprocessor = DataPreprocessor(config)
collector = DataCollector(config)
trainer = ModelTrainer(config, classifier, preprocessor, collector)

result = trainer.train_model(hyperparameter_tuning=False)
print('Training complete!')
print(f'Accuracy: {result.get(\"accuracy\", 0):.4f}')
"
```

## Step 3: Monitor Training Progress

### 3.1 Expected Training Output

```
Starting model training...
Configuration:
  Model type: random_forest
  Max samples: 50,000
  Batch loading: enabled
  Hyperparameter tuning: disabled

Loading training data...
  Loading benign samples...
  [████████████████████] 100% | 30,000/30,000
  Loading malicious samples...
  [████████████████████] 100% | 20,000/20,000
  Total samples: 50,000

Preprocessing data...
  Extracting features...
  Normalizing features...
  Splitting data (70/15/15)...
    Training: 35,000 samples
    Validation: 7,500 samples
    Test: 7,500 samples

Training Random Forest...
  [████████████████████] 100% | Training in progress...

Training complete!
  Training time: 8m 32s
  Model saved to: models/classification_model.pkl

Evaluating model...
  Training accuracy: 0.9876
  Validation accuracy: 0.9854
  Test accuracy: 0.9842
```

### 3.2 Training Metrics

The training process will display:
- **Training accuracy**: Model performance on training set
- **Validation accuracy**: Performance on validation set
- **Test accuracy**: Performance on held-out test set
- **Training time**: Total time taken
- **Model file**: Location of saved model

## Step 4: Verify Model Training

### 4.1 Check Model File

```bash
ls -lh backend/models/classification_model.pkl
```

**Expected:**
- File exists
- Size: 10-50 MB (depending on model complexity)

### 4.2 Verify Model Can Be Loaded

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
    
print('Model loaded successfully!')
print(f'Model type: {type(model_data.get(\"model\", None))}')
print(f'Features: {len(model_data.get(\"feature_names\", []))}')
print(f'Training accuracy: {model_data.get(\"training_accuracy\", 0):.4f}')
"
```

**Expected:**
- Model loads without errors
- Contains model object
- Has feature names
- Has training metrics

## Step 5: Training Optimization Tips

### 5.1 For Faster Training

**Reduce sample count:**
```bash
# In .env
MAX_TRAINING_SAMPLES=50000  # Use 50K instead of 100K
```

**Disable hyperparameter tuning:**
```bash
HYPERPARAMETER_TUNING_ENABLED=false  # Already set
```

**Use smaller model:**
```bash
# In config or training script
n_estimators=100  # Instead of default 200
```

### 5.2 For Better Accuracy

**Increase sample count:**
```bash
MAX_TRAINING_SAMPLES=100000  # Use full subset
```

**Enable hyperparameter tuning** (slower but better):
```bash
HYPERPARAMETER_TUNING_ENABLED=true
```

**Use larger model:**
```bash
n_estimators=300  # More trees
```

### 5.3 Memory Management

**If memory issues occur:**
- Ensure `BATCH_LOADING_ENABLED=true`
- Reduce `MAX_TRAINING_SAMPLES`
- Close other applications
- Use smaller batch sizes in data loading

## Step 6: Training Time Estimates

**For 50K samples:**
- Training time: 5-10 minutes
- Memory usage: 1-3 GB

**Note**: Times are approximate and depend on CPU speed and available RAM.

## Step 7: Troubleshooting

### Issue: Out of Memory

**Symptoms**: Training crashes or system becomes unresponsive

**Solutions**:
1. Reduce `MAX_TRAINING_SAMPLES` to 50000
2. Ensure `BATCH_LOADING_ENABLED=true`
3. Close other applications
4. Restart system to free memory

### Issue: Training Too Slow

**Symptoms**: Training takes >20 minutes

**Solutions**:
1. Reduce sample count
2. Use fewer trees (`n_estimators=100`)
3. Disable hyperparameter tuning
4. Check CPU usage (other processes may be using CPU)

### Issue: Low Accuracy

**Symptoms**: Accuracy <90%

**Solutions**:
1. Increase sample count
2. Check data quality (verify labels)
3. Enable hyperparameter tuning
4. Use more trees in Random Forest

### Issue: Model Not Saving

**Symptoms**: Training completes but no model file

**Solutions**:
1. Check write permissions: `chmod 755 backend/models/`
2. Verify disk space: `df -h`
3. Check error logs for specific errors

### Issue: Import Errors

**Symptoms**: `ModuleNotFoundError` or import failures

**Solutions**:
1. Activate virtual environment: `source venv/bin/activate`
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Check Python path

## Step 8: Training Results

### 8.1 Expected Performance

**For 50K samples:**
- **Accuracy**: 93-97%
- **Precision**: 92-96%
- **Recall**: 92-96%
- **F1-Score**: 92-96%
- Excellent for hackathon demo

### 8.2 Model Artifacts

After training, you'll have:
- **Model file**: `backend/models/classification_model.pkl`
- **Training metrics**: Logged to console and potentially saved to file
- **Feature names**: Stored in model for inference

## Step 9: Verify Training Success

### 9.1 Quick Test

```bash
cd backend
source venv/bin/activate
python -c "
from services.classifier import ClassificationDetector
from config import Config

config = Config()
classifier = ClassificationDetector(config)

# Test prediction
test_features = {
    'packet_size': 1500,
    'protocol': 6,  # TCP
    'src_port': 80,
    'dst_port': 443,
    # ... other features
}

result = classifier.classify(test_features)
print(f'Prediction: {result.get(\"prediction\")}')
print(f'Confidence: {result.get(\"confidence\", 0):.4f}')
"
```

**Expected**: Model makes prediction without errors

## Verification Checklist

- [ ] Training configuration verified
- [ ] Sufficient training data in database (50,000 samples)
- [ ] Training script executed successfully
- [ ] Training completed without errors
- [ ] Model file created: `backend/models/classification_model.pkl`
- [ ] Model can be loaded successfully
- [ ] Training accuracy >95%
- [ ] Validation accuracy >95%
- [ ] Test accuracy >95%
- [ ] Training time <15 minutes
- [ ] Memory usage within limits (<4 GB)

## File Locations

- **Model File**: `backend/models/classification_model.pkl`
- **Training Script**: `backend/scripts/train_from_cicids2018.py`
- **Training Logs**: Console output (or check `training.log` if configured)

## Next Steps

Once training is complete and verified, proceed to:
- **Phase 6**: Model Evaluation - Detailed performance metrics and analysis

## Estimated Time

- **Training**: 5-10 minutes (for 50K samples)
- **Verification**: 5 minutes
- **Total**: 10-20 minutes

## Notes

- Random Forest is chosen for speed and good accuracy
- Hyperparameter tuning is disabled for faster training (can enable later)
- Model is saved automatically after training
- Training metrics are displayed in console
- Model can be retrained with new data if needed
