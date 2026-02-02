# CICIDS 2018 Full Dataset Training Guide

## Overview

This guide explains how to train a high-accuracy Intrusion Detection System (IDS) using the complete CICIDS 2018 dataset on Google Colab.

## Features

✅ **Full CICIDS 2018 Dataset** (~16M samples from all days)
✅ **Advanced Deep Learning** (CNN + Multi-Head Attention)
✅ **GPU Acceleration** (6-10 hours on Colab GPU vs 40+ hours on CPU)
✅ **Comprehensive Metrics** (Accuracy, Precision, Recall, F1, AUC-ROC)
✅ **Production Ready** (Exportable model for deployment)
✅ **No MongoDB Required** (Direct CSV processing)

## Quick Start

### 1. Upload to Google Colab

1. Go to [Google Colab](https://colab.research.google.com/)
2. Click `File` → `Upload notebook`
3. Upload `CICIDS_2018_Full_Training.ipynb`
4. Enable GPU: `Runtime` → `Change runtime type` → `Hardware accelerator` → `GPU` → `Save`

### 2. Run the Notebook

Execute cells sequentially (Shift+Enter) or run all:
- Click `Runtime` → `Run all`
- Training will take 6-10 hours with GPU

### 3. Download Trained Model

The notebook will automatically create a zip file with:
- Trained model (.h5 and SavedModel formats)
- Preprocessor (scaler and feature transformations)
- Evaluation metrics and results
- Training history and plots

## Notebook Structure

### Section 1-2: Setup & Dataset Download
- Installs required packages
- Downloads full CICIDS 2018 dataset from AWS S3
- Total size: ~7GB

### Section 3-5: Data Processing
- Loads all CSV files
- Cleans and preprocesses data
- Handles missing values and outliers
- Creates train/val/test splits (70/15/15)

### Section 6-8: Model Training
- **Model Type**: CNN + Multi-Head Attention (default)
  - Alternative: Deep CNN or Dense networks
- **Architecture**:
  - 3 CNN blocks with increasing filters (128, 256, 512)
  - Multi-head attention (8 heads)
  - Dense layers (512, 256)
  - Dropout and BatchNormalization
- **Optimization**:
  - Adam optimizer
  - Learning rate reduction on plateau
  - Early stopping (patience=15)

### Section 9-10: Evaluation
- Test set evaluation
- Confusion matrix
- ROC-AUC curve
- Precision-Recall curve
- Classification report

### Section 11-13: Export & Summary
- Saves model and artifacts
- Creates downloadable archive
- Generates comprehensive summary

## Expected Performance

Based on CICIDS 2018 full dataset training:

| Metric | Target | Expected |
|--------|--------|----------|
| Accuracy | ≥95% | 96-98% |
| Precision | ≥90% | 92-96% |
| Recall | ≥90% | 94-97% |
| F1-Score | ≥90% | 93-96% |
| AUC-ROC | ≥0.95 | 0.96-0.99 |

## Configuration Options

### Model Types

Change `MODEL_TYPE` in Section 6:

```python
MODEL_TYPE = 'cnn_attention'  # Default: Best accuracy
# MODEL_TYPE = 'deep_cnn'      # Alternative: Faster training
# MODEL_TYPE = 'dense'          # Alternative: Simpler architecture
```

### Sample Mode for Testing

For faster testing with a smaller dataset, modify Section 5:

```python
USE_SAMPLE = True   # Use 10% of data
SAMPLE_FRAC = 0.1   # Adjust percentage
```

### Training Parameters

Adjust in Section 8:

```python
BATCH_SIZE = 256    # Increase for faster training (if GPU memory allows)
EPOCHS = 100        # Maximum epochs (early stopping may stop earlier)
```

## Resource Requirements

### Google Colab Free Tier
- **RAM**: 12GB (sufficient for full dataset)
- **GPU**: T4 (sufficient for training)
- **Storage**: ~15GB temporary
- **Runtime**: 6-10 hours (within free tier limits)

### Google Colab Pro (Recommended)
- **RAM**: 25GB
- **GPU**: V100 or A100 (3-5 hours training time)
- **No runtime limits**

## Troubleshooting

### Out of Memory Errors

1. **Reduce batch size**:
   ```python
   BATCH_SIZE = 128  # or even 64
   ```

2. **Enable sample mode**:
   ```python
   USE_SAMPLE = True
   SAMPLE_FRAC = 0.3  # Use 30% of data
   ```

3. **Use Google Colab Pro** for more RAM

### Runtime Disconnection

If Colab disconnects:
1. Model checkpoints are saved automatically
2. Re-run from Section 11 to recover the best model
3. Or continue training from last checkpoint

### Download Issues

If automatic download fails:
1. Files are saved in `/content/output/`
2. Manually download from Colab file browser (left sidebar)
3. Or use:
   ```python
   from google.colab import files
   files.download('/content/cicids2018_ids_model.zip')
   ```

## Integration with Your IDS

### 1. Extract Downloaded Archive

```bash
unzip cicids2018_ids_model.zip -d trained_model/
```

### 2. Load Model in Backend

```python
import tensorflow as tf
import pickle
import numpy as np

# Load model
model = tf.keras.models.load_model('trained_model/cicids2018_ids_model.h5')

# Load preprocessor
with open('trained_model/preprocessor.pkl', 'rb') as f:
    preprocessor = pickle.load(f)

# Load feature names
import json
with open('trained_model/feature_names.json', 'r') as f:
    feature_data = json.load(f)
    feature_names = feature_data['features']

# Make predictions
def predict_traffic(features):
    # features should be a dict or DataFrame with correct feature names
    X = preprocessor.scaler.transform([features])
    prediction = model.predict(X)
    return 'malicious' if prediction[0][0] > 0.5 else 'benign'
```

### 3. Update Backend Configuration

Update `backend/config.py`:

```python
CLASSIFICATION_MODEL_TYPE = 'tensorflow_cnn'
CLASSIFICATION_MODEL_PATH = '/path/to/cicids2018_ids_model.h5'
CLASSIFICATION_SCALER_PATH = '/path/to/preprocessor.pkl'
```

## Advanced Usage

### Hyperparameter Tuning

For even better results, you can add hyperparameter optimization using Keras Tuner or Optuna (already installed in notebook).

Example with Keras Tuner:

```python
import keras_tuner as kt

def build_model(hp):
    model = keras.Sequential([
        layers.Dense(
            hp.Int('units_1', min_value=256, max_value=1024, step=128),
            activation='relu'
        ),
        layers.Dropout(hp.Float('dropout_1', 0.2, 0.5, step=0.1)),
        layers.Dense(1, activation='sigmoid')
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(
            hp.Float('learning_rate', 1e-4, 1e-2, sampling='log')
        ),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model

tuner = kt.RandomSearch(
    build_model,
    objective='val_accuracy',
    max_trials=20,
    directory='/content/tuner',
    project_name='ids_tuning'
)

tuner.search(X_train_scaled, y_train,
             validation_data=(X_val_scaled, y_val),
             epochs=50)
```

### Transfer Learning

To use the trained model as a base for other datasets:

```python
# Load pre-trained model
base_model = tf.keras.models.load_model('cicids2018_ids_model.h5')

# Freeze base layers
for layer in base_model.layers[:-3]:
    layer.trainable = False

# Add new classification head
x = base_model.layers[-4].output
x = layers.Dense(128, activation='relu')(x)
x = layers.Dropout(0.3)(x)
outputs = layers.Dense(num_classes, activation='softmax')(x)

# Create new model
new_model = keras.Model(inputs=base_model.input, outputs=outputs)

# Fine-tune on new data
new_model.compile(...)
new_model.fit(new_X_train, new_y_train, ...)
```

## Model Performance Breakdown

### Attack Type Detection (Expected)

| Attack Type | Detection Rate |
|-------------|----------------|
| Brute Force | >99% |
| DoS/DDoS | >98% |
| Infiltration | >95% |
| SQL Injection | >97% |
| Bot | >96% |
| Web Attacks | >94% |

### Benign Traffic
- False Positive Rate: <3%
- True Negative Rate: >97%

## Comparison with 50K Sample Model

| Metric | 50K Model | Full Dataset Model |
|--------|-----------|-------------------|
| Training Samples | 50,000 | ~11-16M |
| Training Time | 30 min | 6-10 hours |
| Accuracy | ~92-94% | ~96-98% |
| Generalization | Good | Excellent |
| Attack Coverage | Limited | Comprehensive |

## Support and Improvements

### Future Enhancements
- [ ] Ensemble methods (multiple models voting)
- [ ] Real-time inference optimization
- [ ] Model quantization for edge deployment
- [ ] Continual learning for new attack types
- [ ] Explainable AI (SHAP values for predictions)

### Known Limitations
- Requires periodic retraining (every 3-6 months)
- May not detect zero-day attacks immediately
- Performance depends on feature quality from packet capture

## References

- **Dataset**: [CICIDS 2018](https://www.unb.ca/cic/datasets/ids-2018.html)
- **Paper**: Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization
- **Architecture**: Inspired by state-of-the-art deep learning IDS research

## License

This training notebook is provided for educational and research purposes. The CICIDS 2018 dataset has its own license terms - please review before commercial use.

---

**Questions or Issues?**
- Check the troubleshooting section above
- Review Google Colab documentation
- Check TensorFlow/Keras documentation for model-specific issues
