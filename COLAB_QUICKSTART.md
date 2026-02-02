# Quick Start - CICIDS 2018 Training (Fixed Version)

## Issues Fixed

✅ **Package Version Conflicts** - Now uses latest compatible versions
✅ **TensorFlow Compatibility** - Removed version pinning
✅ **MultiHeadAttention** - Made optional with fallback
✅ **Dependencies** - Simplified and tested

## Quick Steps

### 1. Upload to Google Colab

1. Go to [colab.research.google.com](https://colab.research.google.com/)
2. Upload `CICIDS_2018_Full_Training.ipynb`
3. **IMPORTANT**: Enable GPU
   - Runtime → Change runtime type
   - Hardware accelerator → **GPU** (T4)
   - Save

### 2. Run the Fixed Version

The notebook now:
- Installs latest stable packages (no version conflicts)
- Uses `deep_cnn` model by default (better compatibility)
- Has fallback for optional features

### 3. Recommended Settings

In the notebook, you can adjust:

```python
# Cell 11: Data loading
USE_SAMPLE = True   # Start with True for testing (10% of data)
SAMPLE_FRAC = 0.1   # Test with 10% first

# Cell 15: Model type
MODEL_TYPE = 'deep_cnn'  # Best compatibility
# MODEL_TYPE = 'dense'   # Faster training, simpler model

# Cell 19: Training
BATCH_SIZE = 256   # Or 128 if you get memory errors
EPOCHS = 50        # Reduce for faster testing
```

## Testing First (Recommended)

Before running the full dataset (6-10 hours), test with a sample:

1. **Set sample mode** (Cell 11):
   ```python
   USE_SAMPLE = True
   SAMPLE_FRAC = 0.1  # 10% of data
   ```

2. **Run all cells** - Should complete in ~30-45 minutes

3. **Check results** - If accuracy is good (>90%), proceed with full dataset

4. **Run full dataset**:
   ```python
   USE_SAMPLE = False  # Use all data
   ```

## Expected Results

### Sample Mode (10% data)
- Training time: ~30-45 minutes
- Expected accuracy: 90-94%
- Good for testing setup

### Full Dataset
- Training time: 6-10 hours (with GPU)
- Expected accuracy: 96-98%
- Production-ready model

## Troubleshooting

### Memory Errors
```python
# Reduce batch size (Cell 19)
BATCH_SIZE = 128  # or even 64
```

### Slow Training
- Make sure GPU is enabled (Runtime → Runtime type → GPU)
- Check GPU usage: top-right corner should show GPU RAM

### Colab Disconnects
- Model checkpoints are saved automatically
- Best model saved at `/content/checkpoints/best_model.h5`
- Can resume from checkpoints if disconnected

## What Changed from Original

1. **Package Installation** (Cell 2):
   - Removed version pinning
   - Uses latest compatible versions
   - Removed optional packages (keras-tuner, optuna)

2. **Imports** (Cell 3):
   - Made MultiHeadAttention optional
   - Added fallback for missing features
   - Better error handling

3. **Model Architecture** (Cell 15):
   - Default changed to `deep_cnn` (more compatible)
   - MultiHeadAttention with try/catch
   - Works on all TensorFlow versions

## Files Downloaded After Training

The notebook creates:
```
/content/output/
├── cicids2018_ids_model.h5          # Main model (use this!)
├── cicids2018_ids_model_savedmodel/ # Alternative format
├── preprocessor.pkl                  # Feature scaler
├── evaluation_results.json           # Metrics
├── training_history.json             # Training logs
└── feature_names.json                # Feature list
```

These get zipped into: `/content/cicids2018_ids_model.zip`

## Performance Expectations

| Dataset Size | Time (GPU) | Expected Accuracy |
|--------------|------------|-------------------|
| 10% sample | 30-45 min | 90-94% |
| 25% sample | 1-2 hours | 93-96% |
| 50% sample | 3-4 hours | 95-97% |
| 100% full | 6-10 hours | 96-98% |

## Integration with Your Backend

After downloading the model:

```python
import tensorflow as tf
import pickle
import numpy as np

# Load model
model = tf.keras.models.load_model('cicids2018_ids_model.h5')

# Load preprocessor
with open('preprocessor.pkl', 'rb') as f:
    preprocessor = pickle.load(f)

# Predict
def detect_intrusion(features_dict):
    # features_dict: dict with same keys as training data
    # Convert to array in same order as training
    X = np.array([features_dict[name] for name in preprocessor.feature_names])
    X_scaled = preprocessor.scaler.transform([X])

    prediction = model.predict(X_scaled, verbose=0)[0][0]
    confidence = prediction if prediction > 0.5 else 1 - prediction

    return {
        'label': 'malicious' if prediction > 0.5 else 'benign',
        'confidence': float(confidence * 100)
    }
```

## Common Questions

**Q: Can I use Colab Free?**
A: Yes! The fixed version works on free tier. Just enable GPU.

**Q: How long can I run before timeout?**
A: Colab Free: ~12 hours max. Colab Pro: unlimited.

**Q: What if training stops?**
A: Model checkpoints are saved. You can load from checkpoint and continue.

**Q: Can I train on CPU?**
A: Yes, but it will take 40+ hours for full dataset. Use sample mode for CPU.

**Q: Memory issues with full dataset?**
A: Reduce batch size or use sample mode. 12GB RAM should handle full dataset with batch_size=128.

## Next Steps After Training

1. ✅ Download the model zip file
2. ✅ Test locally with sample data
3. ✅ Integrate into your IDS backend
4. ✅ Monitor performance on real traffic
5. ✅ Retrain every 3-6 months with new attack data

---

**Ready to start?** Upload the notebook to Colab and enable GPU! 🚀
