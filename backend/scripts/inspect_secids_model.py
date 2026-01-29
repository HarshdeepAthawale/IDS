#!/usr/bin/env python3
"""
Inspect SecIDS-CNN .h5 model: input shape, output shape, and output format.
Run from backend/ with: python scripts/inspect_secids_model.py
Requires: SecIDS-CNN.h5 at SecIDS-CNN/SecIDS-CNN.h5 (or set SECIDS_MODEL_PATH).
"""

import os
import sys
from pathlib import Path

# Add backend and project root to path
backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))

def get_default_model_path():
    """Resolve default path to SecIDS-CNN.h5 (project_root/SecIDS-CNN/SecIDS-CNN.h5)."""
    return project_root / "SecIDS-CNN" / "SecIDS-CNN.h5"

def main():
    model_path = os.environ.get("SECIDS_MODEL_PATH") or str(get_default_model_path())
    model_path = Path(model_path)
    if not model_path.exists():
        print(f"Model file not found: {model_path}")
        print("Download SecIDS-CNN.h5 from https://huggingface.co/Keyven/SecIDS-CNN")
        print("and place it at SecIDS-CNN/SecIDS-CNN.h5 or set SECIDS_MODEL_PATH.")
        sys.exit(1)
    print(f"Loading model: {model_path}")
    try:
        import tensorflow as tf
    except ImportError:
        print("TensorFlow not installed. Install with: pip install tensorflow")
        sys.exit(1)
    model = tf.keras.models.load_model(model_path)
    print("\n--- SecIDS-CNN model inspection ---")
    print(f"Input shape:  {model.input_shape}")
    print(f"Output shape: {model.output_shape}")
    # Dummy batch to confirm output format
    import numpy as np
    batch_size = 2
    if len(model.input_shape) == 2:
        # (batch, features)
        n_features = int(model.input_shape[1])
        dummy = np.zeros((batch_size, n_features), dtype=np.float32)
    elif len(model.input_shape) == 3:
        # (batch, time_steps, features)
        n_steps = int(model.input_shape[1])
        n_features = int(model.input_shape[2])
        dummy = np.zeros((batch_size, n_steps, n_features), dtype=np.float32)
    else:
        print("Unexpected input rank; skipping dummy run.")
        sys.exit(0)
    out = model.predict(dummy)
    print(f"Dummy output shape: {out.shape}")
    print(f"Dummy output sample: {out[0]}")
    if out.shape[-1] == 1:
        print("Output format: single probability (malicious); threshold 0.5 for Attack/Benign.")
    elif out.shape[-1] == 2:
        print("Output format: two-class logits/probs [benign, malicious].")
    print("\n--- Use this input shape and feature count for secids_adapter ---")
    sys.exit(0)

if __name__ == "__main__":
    main()
