# backend/api.py
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from metrics import PREDICTION_COUNT, PREDICTION_ERRORS, PREDICTION_LATENCY
from utils import predict_with_model
from model_manager import ModelManager   # if you see import issues, use: from .model_manager import ModelManager
import time
import os
import sqlite3
from typing import Dict, Any
from flask_jwt_extended import jwt_required

api_bp = Blueprint("api", __name__)
_mm = ModelManager(model_root="backend/models")

# ---- Fallback constraints (used only if metadata is missing) ----
# These match your current DB scan: user_id 1..1002, amount min 5.01.
FALLBACK_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    "user_id":   {"min": 1, "max": 1002},
    "amount":    {"min": 5.01},     # keep upper open-ended
    "location":  {"min": 0, "max": 50},
    "hour":      {"min": 0, "max": 23},
    "dayofweek": {"min": 0, "max": 6},
}

DB_PATH = "backend/instance/bankease.db"  # used by optional existence check


def _load_constraints(model_name: str, model_version: str) -> Dict[str, Dict[str, Any]]:
    """
    Load constraints from model metadata; fall back to constants above.
    """
    try:
        resolved = _mm.resolve_version(model_name, model_version)
        meta = _mm.load_metadata(model_name, resolved)
        cons = meta.get("constraints") or {}
        # merge with fallbacks so missing keys still have bounds
        out = dict(FALLBACK_CONSTRAINTS)
        out.update(cons)
        return out
    except Exception:
        return dict(FALLBACK_CONSTRAINTS)


def _check_range(name: str, val: float, cons: Dict[str, Dict[str, Any]], default_min=None, default_max=None) -> str | None:
    rule = cons.get(name, {})
    lo = rule.get("min", default_min)
    hi = rule.get("max", default_max)
    if lo is not None and val < lo:
        return f"{name} must be ≥ {lo}"
    if hi is not None and val > hi:
        return f"{name} must be ≤ {hi}"
    return None


@api_bp.route("/status", methods=["GET"])
def status():
    try:
        models = _mm.status()  # full: version + features + constraints
    except Exception:
        models = {}

    verbose = request.args.get("verbose", "1") == "1"
    if not verbose:
        # keep only the version per model
        models = {k: {"version": v["version"]} for k, v in models.items() if v}

    return jsonify({"status": "API is running", "models": models}), 200



@api_bp.route("/predict", methods=["POST"])
@jwt_required() 
def predict():
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 400

    data = request.get_json(silent=True) or {}

    required = ["user_id", "amount", "location", "hour", "dayofweek"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing field(s): {', '.join(missing)}"}), 400

    model_name = data.get("model", "xgb")
    model_version = data.get("model_version", "current")

    # ---- Enforce constraints BEFORE scoring ----
    cons = _load_constraints(model_name, model_version)

    # Coerce types safely for validation
    try:
        uid = int(data["user_id"])
        amt = float(data["amount"])
        loc = int(data["location"])
        hr  = int(data["hour"])
        dow = int(data["dayofweek"])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid types: expected integers for user_id/location/hour/dayofweek and float for amount."}), 400

    errs = [e for e in [
        _check_range("user_id",   uid, cons),
        _check_range("amount",    amt, cons),
        _check_range("location",  loc, cons),
        _check_range("hour",      hr,  cons),
        _check_range("dayofweek", dow, cons),
    ] if e]

    if errs:
        return jsonify({"error": "; ".join(errs)}), 400

    # (Optional) strict existence check against DB: set CHECK_USER_EXISTS=1 to enable
    if os.getenv("CHECK_USER_EXISTS", "0") == "1" and os.path.exists(DB_PATH):
        try:
            with sqlite3.connect(DB_PATH) as con:
                row = con.execute("SELECT 1 FROM account WHERE user_id=? LIMIT 1", (uid,)).fetchone()
            if row is None:
                return jsonify({"error": f"user_id {uid} does not exist"}), 400
        except Exception:
            # stay neutral on DB errors (don't leak internals)
            pass

    try:
        # measure latency for UI + record Prometheus histogram
        t0 = time.perf_counter()
        with PREDICTION_LATENCY.labels(model_name).time():
            y_hat, p_hat = predict_with_model(
                data, model_name=model_name, model_version=model_version
            )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        PREDICTION_COUNT.labels(model_name).inc()

        # resolve "current" to a concrete version if possible
        try:
            resolved_version = _mm.resolve_version(model_name, model_version)
        except FileNotFoundError:
            resolved_version = model_version

        resp = {
            "prediction": bool(y_hat),
            "model_used": model_name,
            "model_version": resolved_version,
            "latency_ms": latency_ms,
        }
        if p_hat is not None:
            resp["probability"] = float(p_hat)

        return jsonify(resp), 200

    except BadRequest:
        return jsonify({"error": "Bad request"}), 400
    except Exception as e:
        PREDICTION_ERRORS.labels(type=e.__class__.__name__).inc()
        # neutral message; logs/metrics carry details
        return jsonify({"error": "Prediction failed"}), 500
