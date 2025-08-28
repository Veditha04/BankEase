# scripts/migrate_legacy_models.py
import os, json, shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))

legacy = {
    "xgb": os.path.join(ROOT, "backend", "models", "xgb_model.pkl"),
    "rf":  os.path.join(ROOT, "backend", "models", "rf_model.pkl"),
    "lr":  os.path.join(ROOT, "backend", "models", "logistic_model.pkl"),
}
scaler_srcs = [
    os.path.join(ROOT, "backend", "models", "scaler.pkl"),
    os.path.join(ROOT, "backend", "models", "preprocess", "scaler.pkl"),
]

def ensure_dir(p): os.makedirs(p, exist_ok=True)

def migrate_family(family: str, src_path: str):
    version = "v" + datetime.now().strftime("%Y%m%d_%H%M%S")
    fam_dir = os.path.join(ROOT, "backend", "models", family)
    vdir = os.path.join(fam_dir, version)
    ensure_dir(vdir)
    shutil.copy2(src_path, os.path.join(vdir, "model.joblib"))
    meta = {
        "version": version,
        "family": family,
        "created_at": datetime.now().isoformat(),
        "metrics": {"note": "migrated from legacy pickle; metrics unknown"}
    }
    with open(os.path.join(vdir, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)
    with open(os.path.join(fam_dir, "current.txt"), "w") as f:
        f.write(version)
    print(f"Migrated {family} -> {version}")

def migrate_scaler():
    for src in scaler_srcs:
        if os.path.exists(src):
            version = "v" + datetime.now().strftime("%Y%m%d_%H%M%S")
            fam = "preprocess"
            fam_dir = os.path.join(ROOT, "backend", "models", fam)
            vdir = os.path.join(fam_dir, version)
            ensure_dir(vdir)
            shutil.copy2(src, os.path.join(vdir, "scaler.joblib"))
            with open(os.path.join(fam_dir, "current.txt"), "w") as f:
                f.write(version)
            print(f"Migrated scaler -> {version}")
            return
    print("No scaler found to migrate (optional)")

if __name__ == "__main__":
    any_migrated = False
    for fam, src in legacy.items():
        if os.path.exists(src):
            migrate_family(fam, src); any_migrated = True
        else:
            print(f"Skip {fam}: {src} not found")
    migrate_scaler()
    if not any_migrated:
        print("No legacy model pickles found under backend/models/. Nothing to migrate.")
    print("Done.")
