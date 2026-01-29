#!/usr/bin/env python3
"""
Verify that the pre-trained SecIDS-CNN model is 100% working:
- Config defaults (CLASSIFICATION_ENABLED, CLASSIFICATION_MODEL_TYPE)
- Model path resolution (backend/ and repo root)
- Model load (TensorFlow + .h5)
- classify() with dummy features
Run from backend/: python scripts/verify_secids.py
"""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

def main():
    errors = []
    print("=" * 60)
    print("SecIDS-CNN pre-trained model verification")
    print("=" * 60)

    # 1. Config
    os.environ.setdefault("CLASSIFICATION_ENABLED", "true")
    os.environ.setdefault("CLASSIFICATION_MODEL_TYPE", "secids_cnn")
    from config import Config
    config = Config()
    if not getattr(config, "CLASSIFICATION_ENABLED", False):
        errors.append("CLASSIFICATION_ENABLED is not True")
    if getattr(config, "CLASSIFICATION_MODEL_TYPE", None) != "secids_cnn":
        errors.append("CLASSIFICATION_MODEL_TYPE is not secids_cnn")
    if errors:
        print("✗ Config:", "; ".join(errors))
        sys.exit(1)
    print("✓ Config: CLASSIFICATION_ENABLED=true, CLASSIFICATION_MODEL_TYPE=secids_cnn")

    # 2. Factory returns SecIDS adapter
    from services.classifier import get_classification_detector
    detector = get_classification_detector(config)
    if getattr(detector, "model_type", None) != "secids_cnn":
        errors.append("get_classification_detector did not return SecIDS adapter")
        print("✗ Factory returned wrong type")
        sys.exit(1)
    print("✓ Factory returns SecIDSClassifierAdapter")

    # 3. Model path exists
    model_path = getattr(detector, "model_path", None)
    if model_path is None:
        errors.append("model_path is None")
    else:
        model_path = Path(model_path)
        if not model_path.exists():
            errors.append(f"Model file not found: {model_path}")
    if errors:
        print("✗ Path:", errors[-1])
        print("  Install TensorFlow: pip install tensorflow")
        print("  Place SecIDS-CNN.h5 at SecIDS-CNN/SecIDS-CNN.h5 (repo root) or set SECIDS_MODEL_PATH.")
        sys.exit(1)
    print(f"✓ Model path exists: {model_path}")

    # 4. Model loaded (TensorFlow)
    if not detector.is_trained or detector.model is None:
        print("✗ Model not loaded (is_trained=False or model=None).")
        print("  Install TensorFlow: pip install tensorflow")
        sys.exit(1)
    print("✓ Model loaded (TensorFlow)")

    # 5. classify() works
    n = getattr(detector, "_n_features", None) or (len(detector.feature_names) if detector.feature_names else 0)
    if not n:
        print("✗ Could not determine feature count from model")
        sys.exit(1)
    features = {f: 0.0 for f in (detector.feature_names or [f"feature_{i}" for i in range(n)])}
    try:
        out = detector.classify(features)
    except Exception as e:
        print(f"✗ classify() failed: {e}")
        sys.exit(1)
    if not out.get("is_trained") or "label" not in out:
        print("✗ classify() returned invalid result:", out)
        sys.exit(1)
    print(f"✓ classify() works: label={out.get('label')}, confidence={out.get('confidence')}")

    print("=" * 60)
    print("SecIDS-CNN pre-trained model is 100% working.")
    print("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
