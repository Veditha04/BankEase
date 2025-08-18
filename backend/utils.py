# backend/utils.py
import joblib
import numpy as np
import os

# Load model and scaler once
SCALER_PATH = "models/scaler.pkl"
LR_PATH = "models/logistic_model.pkl"
XGB_PATH = "models/xgb_model.pkl"
RF_PATH = "models/rf_model.pkl"

try:
    scaler = joblib.load(SCALER_PATH)
    lr_model = joblib.load(LR_PATH)
    xgb_model = joblib.load(XGB_PATH)
    rf_model = joblib.load(RF_PATH)
except FileNotFoundError as e:
    print(f"⚠️ Model file not found: {e}")
    scaler = lr_model = xgb_model = rf_model = None

def preprocess_input(data_dict):
    """
    Converts dict input into scaled NumPy array for prediction
    """
    features = np.array([
        data_dict['user_id'],
        data_dict['amount'],
        data_dict['location'],
        data_dict['hour'],
        data_dict['dayofweek']
    ]).reshape(1, -1)
    return scaler.transform(features)

def predict_with_model(data_dict, model_name="xgb"):
    """
    Predict fraud using specified model: 'lr', 'xgb', 'rf'
    """
    x = preprocess_input(data_dict)

    if model_name == "lr":
        return int(lr_model.predict(x)[0])
    elif model_name == "rf":
        return int(rf_model.predict(x)[0])
    else:
        return int(xgb_model.predict(x)[0])
