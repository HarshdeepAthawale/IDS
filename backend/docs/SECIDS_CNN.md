# SecIDS-CNN integration

**SecIDS-CNN is the default classifier.** The backend uses only the pre-trained **SecIDS-CNN** Keras model by default (no internal dataset or training). To use the trainable sklearn pipeline (Random Forest, CICIDS2018, etc.) instead, set `CLASSIFICATION_MODEL_TYPE=random_forest`.

## Docker

The Docker image copies `SecIDS-CNN/` (including `SecIDS-CNN.h5`) into the container at build time. Classification defaults are `CLASSIFICATION_ENABLED=true` and `CLASSIFICATION_MODEL_TYPE=secids_cnn`, so SecIDS-CNN is used automatically. See the main [README](../../README.md) “Classification: SecIDS-CNN (default)” section.

## Requirements

- **TensorFlow**: install with `pip install tensorflow` or use the backend `requirements.txt`, which includes `tensorflow>=2.16.0` for Python 3.12 and SecIDS-CNN.
- **Model file**: `SecIDS-CNN.h5` must be downloaded and placed so the backend can load it.

## Getting the model

1. Visit [Hugging Face: Keyven/SecIDS-CNN](https://huggingface.co/Keyven/SecIDS-CNN) and request access if required.
2. Download the model file (e.g. `SecIDS-CNN.h5`).
3. Place it at **`SecIDS-CNN/SecIDS-CNN.h5`** (project root, inside the `SecIDS-CNN` folder), or set the path via environment (see below).

## Configuration

Set the following so the backend uses SecIDS-CNN for classification:

- **`CLASSIFICATION_MODEL_TYPE=secids_cnn`** – Use the SecIDS-CNN model.
- **`CLASSIFICATION_ENABLED=true`** – Enable supervised classification (required for any classifier).
- **`SECIDS_MODEL_PATH`** (optional) – Full path to `SecIDS-CNN.h5`. If unset, the default is `project_root/SecIDS-CNN/SecIDS-CNN.h5`.

Example `.env`:

```bash
CLASSIFICATION_ENABLED=true
CLASSIFICATION_MODEL_TYPE=secids_cnn
# SECIDS_MODEL_PATH=/path/to/SecIDS-CNN.h5   # optional
```

## Inspecting the model

After placing the model file, you can inspect input/output shape and feature count:

```bash
cd backend
python scripts/inspect_secids_model.py
```

See [SECIDS_CNN_INPUT_OUTPUT.md](SECIDS_CNN_INPUT_OUTPUT.md) for how this is used for feature mapping.

## Training and evaluation

SecIDS-CNN is **pre-trained**. The training endpoint and training scripts do not train this model; they return a message that the model is pre-trained. The evaluation endpoints (`/api/training/evaluate`, confusion matrix, training history) return a friendly message when using SecIDS-CNN only (no internal dataset). Model info and metrics (`/api/training/model-info`, `/api/training/metrics`) work as usual.

## Feature mapping

The adapter builds a feature vector from the same feature dict/DataFrame used by the rest of the IDS. Feature count and order are inferred from the model’s input shape when the `.h5` is loaded. For CICIDS-style or flow-level features, ensure your data matches the expected input (see the discovery script output and [SECIDS_CNN_INPUT_OUTPUT.md](SECIDS_CNN_INPUT_OUTPUT.md)).
