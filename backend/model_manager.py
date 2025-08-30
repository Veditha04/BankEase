# backend/model_manager.py
import os
import json
import time
import joblib
import numpy as np
from datetime import datetime
from typing import Any, Dict, Optional, List


class ModelManager:
    """
    Versioned model storage with per-family directories, e.g.:
      backend/models/xgb/v20250828_153012/model.joblib
      backend/models/xgb/v20250828_153012/preprocess.joblib   (optional)
      backend/models/xgb/v20250828_153012/metadata.json        (should include 'features')
      backend/models/xgb/current.txt  -> v20250828_153012
    """
    def __init__(self, model_root: str = "backend/models"):
        self.model_root = model_root
        os.makedirs(self.model_root, exist_ok=True)

    # ---------- Dir helpers ----------
    def _family_dir(self, family: Optional[str]) -> str:
        return os.path.join(self.model_root, family) if family else self.model_root

    def _version_dir(self, family: Optional[str], version: str) -> str:
        return os.path.join(self._family_dir(family), version)

    def _current_pointer_path(self, family: Optional[str]) -> str:
        return os.path.join(self._family_dir(family), "current.txt")

    # ---------- Save / Load ----------
    def save_model(
        self,
        model: Any,
        metrics: Dict[str, float],
        family: Optional[str] = None,
        version: Optional[str] = None,
        preprocess: Any = None,
        features: Optional[List[str]] = None,
    ) -> str:
        """
        Saves model (and optional preprocess) + metadata. Updates current.txt.
        Return the version string used.
        """
        version = version or f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        vdir = self._version_dir(family, version)
        os.makedirs(vdir, exist_ok=True)

        # Save model
        joblib.dump(model, os.path.join(vdir, "model.joblib"))

        # Optional preprocess
        if preprocess is not None:
            joblib.dump(preprocess, os.path.join(vdir, "preprocess.joblib"))

        # Metadata
        meta = {
            "version": version,
            "family": family,
            "created_at": datetime.now().isoformat(),
            "metrics": metrics or {},
        }
        if features:
            meta["features"] = features  # order matters for prediction
        with open(os.path.join(vdir, "metadata.json"), "w") as f:
            json.dump(meta, f, indent=2)

        # Update current pointer (portable, no symlink)
        with open(self._current_pointer_path(family), "w") as f:
            f.write(version)

        return version

    def resolve_version(self, family: Optional[str], version: str) -> str:
        if version == "current":
            ptr = self._current_pointer_path(family)
            if not os.path.exists(ptr):
                raise FileNotFoundError(f"No current model set for family {family!r}")
            with open(ptr, "r") as f:
                version = f.read().strip()
        return version

    def load_model(self, family: Optional[str] = None, version: str = "current") -> Any:
        """
        Backward-compat: returns just the model object.
        Prefer load_artifacts() if you need preprocess + metadata.
        """
        version = self.resolve_version(family, version)
        model_path = os.path.join(self._version_dir(family, version), "model.joblib")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model {family}@{version} not found at {model_path}")
        return joblib.load(model_path)

    def load_metadata(self, family: Optional[str] = None, version: str = "current") -> Dict[str, Any]:
        version = self.resolve_version(family, version)
        meta_path = os.path.join(self._version_dir(family, version), "metadata.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Metadata for {family}@{version} not found")
        with open(meta_path, "r") as f:
            return json.load(f)

    def load_artifacts(self, family: Optional[str] = None, version: str = "current") -> Dict[str, Any]:
        """
        Returns dict with model, preprocess (or None), metadata, family, version.
        """
        version = self.resolve_version(family, version)
        vdir = self._version_dir(family, version)
        model_path = os.path.join(vdir, "model.joblib")
        pp_path = os.path.join(vdir, "preprocess.joblib")
        meta_path = os.path.join(vdir, "metadata.json")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model {family}@{version} not found at {model_path}")

        model = joblib.load(model_path)
        preprocess = joblib.load(pp_path) if os.path.exists(pp_path) else None
        meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}

        return {
            "family": family,
            "version": version,
            "model": model,
            "preprocess": preprocess,
            "meta": meta,
        }

    # ---------- Inference ----------
    def predict(self, artifacts: Dict[str, Any], features_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        features_dict: Python dict with raw inputs from the request/UI.
        Uses feature order from metadata['features'] if present, else a safe default.
        Returns: dict with probability and latency_ms.
        """
        t0 = time.time()

        meta = artifacts.get("meta") or {}
        # DEFAULT ORDER — change if your training uses a different schema
        cols = meta.get("features") or ["amount", "hour", "dayofweek", "location"]

        # Build 2D array in the right order
        x = np.array([[float(features_dict[c]) for c in cols]], dtype=float)

        # Apply preprocess if available
        preprocess = artifacts.get("preprocess")
        if preprocess is not None:
            x = preprocess.transform(x)

        model = artifacts["model"]
        if hasattr(model, "predict_proba"):
            prob = float(model.predict_proba(x)[0, 1])
        else:
            # fallback for regressors / models without predict_proba
            p = float(model.predict(x)[0])
            prob = max(0.0, min(1.0, p))

        ms = int((time.time() - t0) * 1000)
        return {"probability": prob, "latency_ms": ms}

    # ---------- Discovery / status ----------
    def list_families(self) -> List[str]:
        if not os.path.exists(self.model_root):
            return []
        return [
            d for d in os.listdir(self.model_root)
            if os.path.isdir(self._family_dir(d)) and not d.startswith(".")
        ]

    def list_versions(self, family: Optional[str]) -> List[str]:
        fam_dir = self._family_dir(family)
        if not os.path.exists(fam_dir):
            return []
        return sorted(
            [
                d for d in os.listdir(fam_dir)
                if os.path.isdir(os.path.join(fam_dir, d)) and d.startswith("v")
            ],
            reverse=True
        )

    def status(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Returns {"lr": {"version": "...", "features": [...], "constraints": {...}},
           "rf": {...},
            "xgb": {...}}
        """
        out: Dict[str, Optional[Dict[str, Any]]] = {}
        for fam in self.list_families():
            try:
                v = self.resolve_version(fam, "current")
                meta = self.load_metadata(fam, v)
                out[fam] = {"version": v, "features": meta.get("features"),
                "constraints": meta.get("constraints")}
            except Exception:
                out[fam] = None
        return out
    
