# backend/utils.py
import os
import logging
from typing import Tuple, Dict, Any, Optional

import numpy as np
import joblib

# If your backend is a package, you may need: from .model_manager import ModelManager
from model_manager import ModelManager

logger = logging.getLogger("bankease.utils")

# Decision threshold (can override via env)
THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.50"))

# Single source of truth for models
_MM = ModelManager(model_root=os.path.join("backend", "models"))

# ---- Legacy fallback (optional) ------------------------------------------------
# Only used if versioned loading fails. Keeps older *.pkl paths working locally.
_LEGACY_PATHS = {
    "lr": os.path.join("backend", "models", "logistic_model.pkl"),
    "rf": os.path.join("backend", "models", "rf_model.pkl"),
    "xgb": os.path.join("backend", "models", "xgb_model.pkl"),
}

def _try_load_legacy_model(model_name: str) -> Optional[object]:
    path = _LEGACY_PATHS.get(model_name)
    if path and os.path.exists(path):
        logger.warning("Using legacy model path: %s", path)
        return joblib.load(path)
    return None
# -----------------------------------------------------------------------------

def _build_feature_vector(payload: Dict[str, Any], feature_list: Optional[list]) -> np.ndarray:
    """
    Build a 2D numpy array in the correct column order for the model.
    - If metadata has 'features', use that exact order.
    - Otherwise fallback to a safe default order.
    """
    default_order = ["user_id","amount","location","hour","dayofweek"]  # <- adjust if your model differs
    cols = feature_list or default_order

    try:
        row = [float(payload[c]) for c in cols]
    except KeyError as ke:
        missing = str(ke).strip("'")
        raise KeyError(f"Missing required feature '{missing}' for model inference (expected {cols})")
    except ValueError as ve:
        raise ValueError(f"Invalid type in features {cols}: {ve}")

    return np.asarray(row, dtype=float).reshape(1, -1)

def _predict_proba(model, X: np.ndarray) -> float:
    """
    Return probability in [0,1] even if estimator lacks predict_proba.
    """
    # Classic classifiers
    if hasattr(model, "predict_proba"):
        return float(model.predict_proba(X)[0, 1])

    # Margin -> probability (logistic squash) for SVM/linear models
    if hasattr(model, "decision_function"):
        score = float(model.decision_function(X)[0])
        return 1.0 / (1.0 + np.exp(-score))

    # Regressor fallback (clip to [0,1])
    pred = float(model.predict(X)[0])
    return max(0.0, min(1.0, pred))

def predict_with_model(
    data_dict: Dict[str, Any],
    model_name: str = "xgb",
    model_version: str = "current"
) -> Tuple[int, Optional[float]]:
    """
    Predict fraud using the specified model family ('lr' | 'rf' | 'xgb') and version.
    Returns (y_hat, p_hat).
    """
    model_name = model_name.lower()
    if model_name not in {"lr", "rf", "xgb"}:
        raise ValueError(f"Unsupported model '{model_name}'. Use one of: lr, rf, xgb.")

    # 1) Try versioned artifacts (preferred)
    try:
        art = _MM.load_artifacts(family=model_name, version=model_version)
        meta = art.get("meta") or {}
        features = meta.get("features")  # order matters; may be None

        X = _build_feature_vector(data_dict, features)

        # Apply per-version preprocess if present
        preprocess = art.get("preprocess")
        if preprocess is not None:
            X = preprocess.transform(X)

        model = art["model"]
        p_hat = _predict_proba(model, X)
        y_hat = 1 if p_hat >= THRESHOLD else 0
        return y_hat, p_hat

    except FileNotFoundError as e:
        logger.warning("Versioned artifacts not found (%s). Trying legacy paths.", e)

    # 2) Fallback: legacy loose models (no versioning, no preprocess)
    legacy = _try_load_legacy_model(model_name)
    if legacy is None:
        # Nothing else we can do; let API bubble up a neutral 500.
        raise FileNotFoundError(
            f"No versioned artifacts and no legacy model found for '{model_name}'. "
            f"Expected versioned under backend/models/{model_name}/v*/ "
            f"with current.txt pointer."
        )

    # Build with default order for legacy models
    X = _build_feature_vector(data_dict, feature_list=None)
    p_hat = _predict_proba(legacy, X)
    y_hat = 1 if p_hat >= THRESHOLD else 0
    return y_hat, p_hat
