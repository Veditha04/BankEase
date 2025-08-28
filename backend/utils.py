# backend/utils.py
import os
import logging
import joblib
import numpy as np
from typing import Tuple, Optional

from model_manager import ModelManager

logger = logging.getLogger("bankease.utils")

# ---------------------------------------------------------------------
# Scaler handling
# We try a few common locations to keep backward-compat with your repo.
# Preferred: backend/models/preprocess/current.txt -> v.../scaler.joblib
# Fallbacks: models/scaler.pkl (legacy) or backend/models/scaler.pkl
# ---------------------------------------------------------------------

def _find_legacy_scaler_paths():
    return [
        os.path.join("backend", "models", "scaler.pkl"),
        os.path.join("models", "scaler.pkl"),
        os.path.join("backend", "models", "preprocess", "scaler.pkl"),
    ]

def _load_versioned_scaler() -> Optional[object]:
    """
    Try to load a versioned scaler via ModelManager under family 'preprocess'.
    Expect:
      backend/models/preprocess/vYYYY.../scaler.joblib
      backend/models/preprocess/current.txt -> vYYYY...
    """
    mm = ModelManager(model_root=os.path.join("backend", "models"))
    try:
        version = mm.resolve_version("preprocess", "current")
        scaler_path = os.path.join("backend", "models", "preprocess", version, "scaler.joblib")
        if os.path.exists(scaler_path):
            return joblib.load(scaler_path)
    except FileNotFoundError:
        pass
    return None

def _load_legacy_scaler() -> Optional[object]:
    for p in _find_legacy_scaler_paths():
        if os.path.exists(p):
            return joblib.load(p)
    return None

# Load scaler once (prefer versioned, then legacy). Raise if none found.
_SCALER = _load_versioned_scaler() or _load_legacy_scaler()
if _SCALER is None:
    # Let the API’s error handler convert this to a 500 with a neutral message
    raise FileNotFoundError(
        "Feature scaler not found. Expected versioned scaler under "
        "'backend/models/preprocess/current.txt' (-> v.../scaler.joblib) "
        "or a legacy scaler at 'models/scaler.pkl'."
    )

# ---------------------------------------------------------------------
# Model loading via ModelManager
# We assume families: 'lr', 'rf', 'xgb'
# Directory structure (example):
#   backend/models/xgb/vYYYYMMDD_HHMMSS/model.joblib
#   backend/models/xgb/vYYYYMMDD_HHMMSS/metadata.json
#   backend/models/xgb/current.txt -> vYYYY...
# For backward-compat, we also support legacy files in models/*.pkl
# ---------------------------------------------------------------------

_MM = ModelManager(model_root=os.path.join("backend", "models"))

def _load_legacy_model(model_name: str):
    legacy_map = {
        "lr": os.path.join("models", "logistic_model.pkl"),
        "rf": os.path.join("models", "rf_model.pkl"),
        "xgb": os.path.join("models", "xgb_model.pkl"),
    }
    path = legacy_map.get(model_name)
    if path and os.path.exists(path):
        return joblib.load(path)
    return None

def _load_model(model_name: str, model_version: str = "current"):
    """
    Load a model by family ('lr'|'rf'|'xgb') and version.
    Prefer versioned ModelManager; fall back to legacy file if not found.
    """
    try:
        return _MM.load_model(family=model_name, version=model_version)
    except FileNotFoundError:
        legacy = _load_legacy_model(model_name)
        if legacy is not None:
            # Best-effort: emulate a "current" pointer for legacy path
            return legacy
        raise  # propagate; API will respond with a neutral 500

# ---------------------------------------------------------------------
# Preprocessing and prediction
# Keep feature order consistent with training.
# Your previous code used: [user_id, amount, location, hour, dayofweek]
# NOTE: Consider removing user_id from model features in future; it can leak identity.
# ---------------------------------------------------------------------

def preprocess_input(data_dict: dict) -> np.ndarray:
    """
    Converts dict input into scaled NumPy array for prediction.
    Expects keys: user_id, amount, location, hour, dayofweek
    """
    # Preserve original feature order used during training:
    raw = np.array([
        data_dict["user_id"],
        float(data_dict["amount"]),
        float(data_dict["location"]),
        int(data_dict["hour"]),
        int(data_dict["dayofweek"]),
    ], dtype=float).reshape(1, -1)

    # Apply scaler (loaded at import)
    return _SCALER.transform(raw)

def _predict_proba_if_available(model, x: np.ndarray) -> Optional[float]:
    """
    Returns P(y=1) if the model can produce it, else None.
    """
    if hasattr(model, "predict_proba"):
        try:
            return float(model.predict_proba(x)[0][1])
        except Exception:
            return None
    if hasattr(model, "decision_function"):
        try:
            score = float(model.decision_function(x)[0])
            # logistic squash
            return 1.0 / (1.0 + np.exp(-score))
        except Exception:
            return None
    return None

def predict_with_model(
    data_dict: dict,
    model_name: str = "xgb",
    model_version: str = "current"
) -> Tuple[int, Optional[float]]:
    """
    Predict fraud using specified model family ('lr' | 'rf' | 'xgb') and version.
    Returns (y_hat, p_hat) where:
      - y_hat is int in {0,1}
      - p_hat is float in [0,1] or None if not available
    """
    # Validate model_name
    if model_name not in {"lr", "rf", "xgb"}:
        raise ValueError(f"Unsupported model '{model_name}'. Use one of: lr, rf, xgb.")

    x = preprocess_input(data_dict)
    model = _load_model(model_name=model_name, model_version=model_version)

    # Binary prediction
    y_hat = int(model.predict(x)[0])

    # Probability if available
    p_hat = _predict_proba_if_available(model, x)

    return y_hat, p_hat
