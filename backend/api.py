# backend/api.py
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from metrics import PREDICTION_COUNT, PREDICTION_ERRORS, PREDICTION_LATENCY
from utils import predict_with_model          # uses your existing backend/utils.py
from model_manager import ModelManager        # uses your existing backend/model_manager.py

api_bp = Blueprint("api", __name__)
_mm = ModelManager(model_root="backend/models")

@api_bp.route("/status", methods=["GET"])
def status():
    # neutral status (no emoji)
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
        # time just the inference
        with PREDICTION_LATENCY.labels(model_name).time():
            y_hat, p_hat = predict_with_model(
                data, model_name=model_name, model_version=model_version
            )

        # success → count it
        PREDICTION_COUNT.labels(model_name).inc()

        # Resolve "current" to a concrete version string
        try:
            resolved_version = _mm.resolve_version(model_name, model_version)
        except FileNotFoundError:
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
    except Exception as e:
        # error → count it and return neutral 500
        PREDICTION_ERRORS.labels(type=e.__class__.__name__).inc()
        return jsonify({"error": "Prediction failed"}), 500
