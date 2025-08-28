BankEase – Fraud Detection System

BankEase is an end-to-end project that simulates how a financial institution could screen transactions for fraud. It combines a Flask backend API with a Streamlit frontend, and it emphasizes reproducibility, model versioning, and production-style practices.

This project was built to demonstrate not just machine learning, but also the engineering discipline needed to serve models reliably.

Key Features
Backend (Flask API)

/api/predict returns:

prediction (fraud / legitimate)

probability (fraud likelihood score)

model_used and model_version

/api/status health check

Account and transaction simulation with registration, login, transfers, and balance checks

Centralized error handling with clear, neutral responses

CORS restricted to known frontend origins

Model Management

Three model families supported: Logistic Regression, Random Forest, XGBoost

Versioned model storage under backend/models/<family>/vYYYYMMDD_HHMMSS/ with current.txt pointer

Scaler versioning under backend/models/preprocess/

Utility scripts to migrate legacy pickles into versioned layouts

Frontend (Streamlit UI)

Clean web interface for entering transactions (user_id, amount, location, hour, dayofweek)

Displays:

fraud probability (with progress bar + metric)

model family and active version

request latency

Allows pinning a specific model version to test rollbacks and reproducibility

Neutral, professional styling (no emojis, recruiter-ready presentation)

Project Layout
BankEase/
├── backend/
│   ├── app.py            # Flask application, DB models, routes
│   ├── api.py            # API blueprint
│   ├── utils.py          # Preprocessing + prediction helpers
│   ├── model_manager.py  # Versioned model manager
│   ├── models/           # Versioned models (lr, rf, xgb, preprocess)
│   └── ...
├── streamlit_app/
│   ├── fraud_ui.py       # Streamlit UI
│   └── config.toml       # Theme configuration
├── scripts/              # Migration / model utilities
├── docs/                 # Screenshots and documentation assets
├── requirements.txt
└── README.md

How to Run
1. Clone & Install
git clone https://github.com/<your-username>/BankEase.git
cd BankEase
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

2. Start the Backend
python backend/app.py


Backend available at http://localhost:5050/api

3. Start the Frontend
streamlit run streamlit_app/fraud_ui.py


Frontend available at http://localhost:8501

Example API Usage

Request:

curl -s -X POST http://localhost:5050/api/predict \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"amount":99,"location":0,"hour":10,"dayofweek":2,"model":"xgb"}'


Response:

{
  "prediction": false,
  "probability": 0.00001545,
  "model_used": "xgb",
  "model_version": "v20250828_152717"
}

Screenshots

(Add your own screenshots here to demonstrate the frontend and results, e.g., docs/screenshot_ui.png)

Why This Project Matters

Most ML demos stop at a Jupyter notebook. BankEase goes further:

Models are versioned with clear pin/rollback capability.

The API provides probability outputs suitable for threshold tuning.

The frontend shows both results and system metadata (model version, latency).

Practices like error handling, CORS hardening, and .gitignore hygiene make the repo closer to a production project.

This balance of modeling and engineering makes BankEase a strong portfolio piece for software + data roles.

License

MIT License