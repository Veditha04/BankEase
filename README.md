# BankEase – Fraud Detection System

BankEase is an end-to-end demo of how a bank could screen transactions for fraud. It pairs a **Flask REST API** with a **Streamlit UI**, serves **versioned ML models** (Logistic Regression, Random Forest, XGBoost), and returns calibrated probabilities with the **model family, version, and latency** for full traceability. The backend includes **JWT authentication**, **CORS**, structured error handling, and **Prometheus metrics**—showcasing reproducible model registry and production-style patterns in a compact project.

## Features

- **Versioned model registry**
  - `backend/models/<family>/vYYYYMMDD_HHMMSS/{model.joblib, metadata.json}`
  - `current.txt` pointer per family; `metadata.json` includes `features` and input **constraints**
- **API**
  - `/api/predict` → `{prediction, probability, model_used, model_version, latency_ms}`
  - `/api/status` → model pointers + constraints for the UI
  - JWT-protected routes; CORS allowlist; unified JSON errors
- **UI (Streamlit)**
  - Single-transaction scoring, **model comparison**, **what-if** analysis, **batch CSV** scoring
  - Sidebar shows model versions and adjustable decision threshold
- **Ops**
  - Prometheus exporter (default `:9100`)
  - `.gitignore` keeps large binaries out; pointers/metadata are committed

##   Getting Started

### 1) Create and activate a virtualenv
```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure the backend

Create a .env file with local defaults:

```bash
cat > .env <<'ENV'
FLASK_ENV=development
PORT=5050
JWT_SECRET_KEY=change-me
JWT_ACCESS_TOKEN_EXPIRES_HOURS=8
METRICS_PORT=9100
ENV
```

### 4) Run the API

```bash
python backend/app.py
```

API:     http://localhost:5050/api
Metrics: http://localhost:9100/

Keep this terminal running. Open a new terminal (activate the venv again) for the next steps.
### 5) Get a JWT and Authenticated prediction
Login and capture the token in $TOKEN

```bash
TOKEN=$(curl -s -X POST http://localhost:5050/login \
  -H "Content-Type: application/json" \
  -d '{"username":"john_doe","password":"test123"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

Quick check: should print a long string with two dots
echo "$TOKEN"

Make an authenticated prediction request
``` bash
curl -s -X POST http://localhost:5050/api/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"amount":120.5,"location":3,"hour":22,"dayofweek":5,"model":"xgb"}' \
  | python -m json.tool
```

Windows PowerShell users can replace the TOKEN=$(...) line with:

```
$resp = Invoke-RestMethod -Method Post -Uri http://localhost:5050/login -ContentType 'application/json' -Body '{"username":"john_doe","password":"test123"}'
$env:TOKEN = $resp.access_token
```

### 6) Configure Streamlit secrets and Run the Streamlit UI

Configure the UI to talk to your API:

```bash
mkdir -p .streamlit
cat > .streamlit/secrets.toml <<'TOML'
API_BASE = "http://localhost:5050/api"
# Optional prefill for the sidebar login:
# LOGIN_USERNAME = "john_doe"
# LOGIN_PASSWORD = "test123"
TOML
```

Start Streamlit:

```
streamlit run streamlit_app/fraud_ui.py
```
UI: http://localhost:8501

### 7) Interact with the UI

In the left sidebar of the UI, either paste your JWT token or use the Login form.
Use the sidebar to Login (or paste your JWT) and try:

- Single-transaction scoring

- Compare across models

- What-if: vary amount

- Batch score CSV

To stop services, press Ctrl+C in the terminals running Flask and Streamlit.

### Mertics Notes
Prometheus metrics are exposed at http://localhost:9100/metrics
Key series: prediction_latency_seconds_*, prediction_count_total, prediction_errors_total.

### Configuration (env vars)

The backend reads .env at the repo root.
| Variable                         | Default       | Purpose                                               |
| -------------------------------- | ------------- | ----------------------------------------------------- |
| `FLASK_ENV`                      | `development` | Dev behavior/logging.                                 |
| `PORT`                           | `5050`        | Flask API port.                                       |
| `JWT_SECRET_KEY`                 | *(required)*  | Secret for signing JWTs.                              |
| `JWT_ACCESS_TOKEN_EXPIRES_HOURS` | `8`           | Access token lifetime (hours).                        |
| `METRICS_PORT`                   | `9100`        | Prometheus exporter port.                             |
| `FRONTEND_ORIGINS`               | *(unset)*     | CORS allowlist (comma-separated URLs) for production. |

