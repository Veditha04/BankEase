# backend/api.py
from flask import Blueprint, request, jsonify
from utils import preprocess_input, predict_with_model

api_bp = Blueprint("api", __name__)

@api_bp.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "API is running 🚀"}), 200

@api_bp.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()

    # Input validation
    required_fields = ["user_id", "amount", "location", "hour", "dayofweek"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Optional: Choose model via query param or JSON body
    model_name = data.get("model", "xgb")

    try:
        prediction = predict_with_model(data, model_name)
        return jsonify({
            "prediction": bool(prediction),
            "model_used": model_name
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
