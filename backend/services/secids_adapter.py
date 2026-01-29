"""
SecIDS-CNN adapter: implements ClassificationDetector interface using the pre-trained
SecIDS-CNN Keras model. Use when CLASSIFICATION_MODEL_TYPE == 'secids_cnn'.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Backend dir = backend/services; backend root = backend/; repo root = backend's parent
_BACKEND_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _BACKEND_DIR.parent
_REPO_ROOT = _BACKEND_ROOT.parent


def _resolve_secids_model_path(config) -> Path:
    """Resolve path to SecIDS-CNN.h5 from config or default.
    Tries: (1) SECIDS_MODEL_PATH, (2) backend/SecIDS-CNN/ (Docker), (3) repo_root/SecIDS-CNN/ (local).
    """
    path = getattr(config, 'SECIDS_MODEL_PATH', None)
    if path:
        return Path(path)
    # Docker: COPY SecIDS-CNN ./SecIDS-CNN with WORKDIR /app/backend → backend/SecIDS-CNN/
    candidate_backend = _BACKEND_ROOT / 'SecIDS-CNN' / 'SecIDS-CNN.h5'
    if candidate_backend.exists():
        return candidate_backend
    # Local: SecIDS-CNN often at repo root
    candidate_repo = _REPO_ROOT / 'SecIDS-CNN' / 'SecIDS-CNN.h5'
    return candidate_repo


class SecIDSClassifierAdapter:
    """
    Adapter that wraps the SecIDS-CNN .h5 model and exposes the same interface
    as ClassificationDetector (classify, predict, predict_proba, is_trained, etc.).
    """

    def __init__(self, config):
        self.config = config
        self.model = None
        self.model_path = _resolve_secids_model_path(config)
        self.is_trained = False
        self.model_type = 'secids_cnn'
        self.model_metadata = {}
        self.feature_names = None  # Set from model input shape; used for mapping
        self._input_shape = None   # (batch, features) or (batch, steps, features)
        self._n_features = None
        self._expects_3d = False
        self._load_model()

    def _load_model(self):
        """Load the Keras .h5 model and infer input shape."""
        if not self.model_path.exists():
            logger.warning(
                f"SecIDS-CNN model not found at {self.model_path}. "
                "Download from https://huggingface.co/Keyven/SecIDS-CNN and set SECIDS_MODEL_PATH or place at SecIDS-CNN/SecIDS-CNN.h5"
            )
            return
        try:
            import tensorflow as tf
            self.model = tf.keras.models.load_model(self.model_path)
            self.is_trained = True
            inp_shape = getattr(self.model, 'input_shape', None)
            if isinstance(inp_shape, (list, tuple)) and inp_shape:
                inp_shape = inp_shape[0] if isinstance(inp_shape[0], (list, tuple)) else inp_shape
            self._input_shape = inp_shape
            if inp_shape and len(inp_shape) >= 2:
                if len(inp_shape) == 2:
                    self._n_features = int(inp_shape[1]) if inp_shape[1] else None
                    self._expects_3d = False
                elif len(inp_shape) == 3:
                    self._n_features = (int(inp_shape[1]) or 1) * (int(inp_shape[2]) or 1)
                    self._expects_3d = True
                else:
                    self._n_features = int(inp_shape[-1]) if inp_shape[-1] else None
                if self._n_features:
                    self.feature_names = [f'feature_{i}' for i in range(self._n_features)]
            logger.info(f"SecIDS-CNN loaded from {self.model_path}, input_shape={inp_shape}")
        except ImportError:
            logger.warning("TensorFlow not installed. Install with: pip install tensorflow. SecIDS-CNN will be disabled.")
        except Exception as e:
            logger.error(f"Failed to load SecIDS-CNN model: {e}")
            self.is_trained = False

    def _features_dict_to_array(self, features: Dict[str, float]) -> np.ndarray:
        """Build a single-sample array from features dict; pad/truncate to model input size."""
        if self.feature_names:
            vals = [float(features.get(name, 0.0)) for name in self.feature_names]
        else:
            keys = sorted(features.keys())
            vals = [float(features.get(k, 0.0)) for k in keys]
        n = self._n_features or len(vals)
        if len(vals) < n:
            vals = vals + [0.0] * (n - len(vals))
        elif len(vals) > n:
            vals = vals[:n]
        arr = np.array([vals], dtype=np.float32)
        if self._expects_3d and self._input_shape and len(self._input_shape) == 3:
            steps = int(self._input_shape[1]) or 1
            f = int(self._input_shape[2]) or n
            arr = arr.reshape((1, steps, f))
        return arr

    def _prepare_batch(self, X: np.ndarray) -> np.ndarray:
        """Ensure batch X matches model input shape (2D or 3D)."""
        X = np.asarray(X, dtype=np.float32)
        if self._expects_3d and self._input_shape and len(self._input_shape) == 3:
            steps = int(self._input_shape[1]) or 1
            f = int(self._input_shape[2])
            if X.ndim == 2 and X.shape[1] == steps * f:
                X = X.reshape((-1, steps, f))
        return X

    def _raw_predict(self, X: np.ndarray) -> np.ndarray:
        """Run model.predict and return raw output (probabilities)."""
        if not self.is_trained or self.model is None:
            raise RuntimeError("SecIDS-CNN model not loaded")
        X = self._prepare_batch(X)
        out = self.model.predict(X, verbose=0)
        if hasattr(out, 'numpy'):
            out = out.numpy()
        return np.asarray(out)

    def classify(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Single-sample classification; same interface as ClassificationDetector.classify."""
        try:
            if not self.is_trained:
                return {
                    'label': 'unknown',
                    'confidence': 0.0,
                    'is_trained': False
                }
            X = self._features_dict_to_array(features)
            raw = self._raw_predict(X)
            # Output: (1, 1) single prob or (1, 2) two-class
            if raw.ndim == 2 and raw.shape[1] == 1:
                p_malicious = float(raw[0, 0])
            elif raw.ndim == 2 and raw.shape[1] >= 2:
                p_malicious = float(raw[0, 1])
            else:
                p_malicious = float(raw.flatten()[0])
            p_benign = 1.0 - p_malicious
            label = 'malicious' if p_malicious > 0.5 else 'benign'
            confidence = p_malicious if label == 'malicious' else p_benign
            return {
                'label': label,
                'confidence': confidence,
                'is_trained': True,
                'probabilities': {'benign': p_benign, 'malicious': p_malicious}
            }
        except Exception as e:
            logger.error(f"SecIDS classify error: {e}")
            return {'label': 'unknown', 'confidence': 0.0, 'error': str(e)}

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Batch prediction; returns 0/1 array (0=benign, 1=malicious)."""
        if not self.is_trained:
            return np.zeros(len(X), dtype=np.int64)
        raw = self._raw_predict(X)
        if raw.ndim == 2 and raw.shape[1] == 1:
            probs = raw[:, 0]
        elif raw.ndim == 2 and raw.shape[1] >= 2:
            probs = raw[:, 1]
        else:
            probs = raw.flatten()
        return (np.asarray(probs) > 0.5).astype(np.int64)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Batch probability prediction; returns (N, 2) [p_benign, p_malicious]."""
        if not self.is_trained:
            return np.tile([1.0, 0.0], (len(X), 1))
        raw = self._raw_predict(X)
        if raw.ndim == 2 and raw.shape[1] == 1:
            p_mal = raw[:, 0]
            return np.column_stack([1.0 - p_mal, p_mal])
        if raw.ndim == 2 and raw.shape[1] >= 2:
            return np.asarray(raw[:, :2], dtype=np.float64)
        p_mal = raw.flatten()
        return np.column_stack([1.0 - p_mal, p_mal])

    def get_model_info(self) -> Dict[str, Any]:
        """Same interface as ClassificationDetector.get_model_info."""
        return {
            'model_type': self.model_type,
            'is_trained': self.is_trained,
            'model_path': str(self.model_path),
            'metadata': self.model_metadata,
            'input_shape': str(self._input_shape) if self._input_shape else None
        }

    def get_feature_importance(self) -> Dict[str, float]:
        """SecIDS-CNN does not expose feature importance; return empty dict."""
        return {}

    @property
    def n_features_in_(self) -> Optional[int]:
        """Sklearn-like attribute for feature count (e.g. used by verify_system_complete)."""
        return self._n_features if self._n_features is not None else 0
