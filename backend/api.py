# backend/api.py
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest

from utils import predict_with_model   # returns (y_hat, p_hat)
from model_manager import ModelManager                    # <- add

api_bp = Blueprint("api", __name__)
_mm = ModelManager(model_root="backend/models")           # <- add

@api_bp.route("/status", methods=["GET"])
def status():
    # keep neutral status (no emoji)
    return jsonify({"status": "API is running"}), 200


@api_bp.route("/predict", methods=["POST"])
def predict():
    # Content-type check
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 400

    data = request.get_json(silent=True) or {}

    # Required fields
    required = ["user_id", "amount", "location", "hour", "dayofweek"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing field(s): {', '.join(missing)}"}), 400

    # Optional selectors
    model_name = data.get("model", "xgb")           # 'lr' | 'rf' | 'xgb'
    model_version = data.get("model_version", "current")

    try:
        # Predict (utils uses ModelManager under the hood)
        y_hat, p_hat = predict_with_model(
            data, model_name=model_name, model_version=model_version
        )

        # Resolve the "current" pointer to a concrete version string
        try:
            resolved_version = _mm.resolve_version(model_name, model_version)
        except FileNotFoundError:
            # if you’re still on legacy files, fall back to whatever was requested
            resolved_version = model_version

        resp = {
            "prediction": bool(y_hat),
            "model_used": model_name,
            "model_version": resolved_version,
        }
        if p_hat is not None:
            resp["probability"] = float(p_hat)

        return jsonify(resp), 200

    except BadRequest:
        return jsonify({"error": "Bad request"}), 400
    except Exception:
        # your app-level error handler will log details
        return jsonify({"error": "Prediction failed"}), 500
