# BankEase – Fraud Detection System

**BankEase** is an end-to-end project that simulates how a financial institution could screen transactions for fraud.  
It combines a **Flask backend API** with a **Streamlit frontend**, and emphasizes reproducibility, model versioning, and production-style practices.

---

## Key Features

### Backend (Flask API)
- `/api/predict` returns:
  - `prediction` (fraud / legitimate)  
  - `probability` (fraud likelihood score)  
  - `model_used` and `model_version`
- `/api/status` health check
- Account + transaction simulation (register, login, transfer, balance)
- Centralized error handling (neutral JSON responses)
- CORS restricted to known frontend origins

### Model Management
- Supports Logistic Regression, Random Forest, and XGBoost  
- Versioned model storage:  

backend/models/<family>/vYYYYMMDD_HHMMSS/
backend/models/<family>/current.txt

- Versioned scaler:  


backend/models/preprocess/vYYYY.../scaler.joblib
backend/models/preprocess/current.txt


### Frontend (Streamlit UI)
- Clean form to enter transaction data (`user_id, amount, location, hour, dayofweek`)
- Shows:
- Fraud probability (metric + progress bar)  
- Model family + active version  
- Request latency (ms)
- Can pin a specific model version
- Professional neutral styling

---


## How to Run

### 1) Backend
```bash
python backend/app.py
Runs at: http://localhost:5050/api



### 2) Frontend
streamlit run streamlit_app/fraud_ui.py
Runs at: http://localhost:8501

Example API Call

Request

curl -s -X POST http://localhost:5050/api/predict \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"amount":99,"location":0,"hour":10,"dayofweek":2,"model":"xgb"}'


Response

{
  "prediction": false,
  "probability": 0.00001545,
  "model_used": "xgb",
  "model_version": "v20250828_152717"
}
