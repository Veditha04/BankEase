# backend/model_manager.py
import os
import json
import joblib
from datetime import datetime
from typing import Any, Dict, Optional, List

class ModelManager:
    """
    Versioned model storage with per-family directories, e.g.:
      backend/models/xgb/v20250828_153012/model.joblib
      backend/models/xgb/v20250828_153012/metadata.json
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
        self, model: Any, metrics: Dict[str, float],
        family: Optional[str] = None, version: Optional[str] = None
    ) -> str:
        version = version or f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        vdir = self._version_dir(family, version)
        os.makedirs(vdir, exist_ok=True)

        # Save model and metadata
        joblib.dump(model, os.path.join(vdir, "model.joblib"))
        meta = {
            "version": version,
            "family": family,
            "created_at": datetime.now().isoformat(),
            "metrics": metrics,
        }
        with open(os.path.join(vdir, "metadata.json"), "w") as f:
            json.dump(meta, f, indent=2)

        # Update current pointer (portable, no symlink needed)
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

    # ---------- Discovery (optional) ----------
    def list_families(self) -> List[str]:
        return [d for d in os.listdir(self.model_root) if os.path.isdir(self._family_dir(d))]

    def list_versions(self, family: Optional[str]) -> List[str]:
        fam_dir = self._family_dir(family)
        if not os.path.exists(fam_dir):
            return []
        return sorted(
            [d for d in os.listdir(fam_dir) if os.path.isdir(os.path.join(fam_dir, d)) and d.startswith("v")],
            reverse=True
        )
