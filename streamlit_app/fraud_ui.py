# streamlit_app/fraud_ui.py
import time
import json
import requests
import streamlit as st
from style_helper import inject_noise_gradient  # or inject_diagonal_hatch / inject_subtle_grid
inject_noise_gradient()


# ----- Configuration -----
# You can override API_BASE by creating .streamlit/secrets.toml with:
# API_BASE = "http://localhost:5050/api"
API_BASE = st.secrets.get("API_BASE", "http://localhost:5050/api")

st.set_page_config(page_title="BankEase – Fraud Screening", layout="centered")

# ----- Header -----
st.title("BankEase – Transaction Screening")
st.caption("Enter a transaction to estimate fraud likelihood.")

# ----- Input form (matches backend contract) -----
with st.form("fraud_form", clear_on_submit=False):
    c1, c2 = st.columns(2)

    with c1:
        user_id = st.number_input("User ID", min_value=0, value=1, step=1, help="Synthetic user id used by the model.")
        amount = st.number_input("Amount ($)", min_value=0.0, value=99.0, step=1.0)
        location = st.number_input("Location (encoded)", min_value=0, value=0, step=1, help="Preprocessed/encoded location.")

    with c2:
        hour = st.number_input("Hour (0–23)", min_value=0, max_value=23, value=10, step=1)
        dayofweek = st.number_input("Day of Week (0=Mon … 6=Sun)", min_value=0, max_value=6, value=2, step=1)
        model = st.selectbox("Model family", options=["xgb", "rf", "lr"], index=0)

    with st.expander("Advanced (optional)"):
        model_version = st.text_input(
            "Model version",
            value="current",
            help="Use 'current' or a specific saved version like vYYYYMMDD_HHMMSS.",
        )

    submitted = st.form_submit_button("Score transaction")

# ----- Call backend -----
if submitted:
    payload = {
        "user_id": int(user_id),
        "amount": float(amount),
        "location": int(location),
        "hour": int(hour),
        "dayofweek": int(dayofweek),
        "model": model,
        "model_version": model_version or "current",
    }

    t0 = time.perf_counter()
    try:
        resp = requests.post(f"{API_BASE}/predict", json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        st.error(f"Network error contacting API: {e}")
    else:
        latency_ms = (time.perf_counter() - t0) * 1000.0

        if resp.status_code != 200:
            # Neutral error display
            try:
                info = resp.json()
            except Exception:
                info = {"error": "Unknown error"}
            st.error(f"Request failed ({resp.status_code}): {info.get('error','')}")
        else:
            data = resp.json()

            # ----- Header line with provenance -----
            st.subheader("Result")
            st.caption(
                f"Model: **{data.get('model_used','?')}** · "
                f"Version: **{data.get('model_version','?')}** · "
                f"Latency: **{latency_ms:.1f} ms**"
            )

            # ----- Probability + decision -----
            prob = data.get("probability", None)
            pred = bool(data.get("prediction", False))

            if prob is not None:
                pct = max(0.0, min(1.0, float(prob)))
                st.metric("Fraud probability", f"{pct*100:.2f}%")
                st.progress(pct)
            else:
                st.info("Model did not return a probability; showing class label only.")

            st.write("Decision:", "**FRAUD**" if pred else "**LEGIT**")

            # Optional: show the raw API payload/response for reviewers
            with st.expander("Details (request/response)"):
                st.code("Request:\n" + json.dumps(payload, indent=2))
                st.code("Response:\n" + json.dumps(data, indent=2))
