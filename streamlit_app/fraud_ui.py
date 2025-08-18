# streamlit_app/fraud_ui.py

from matplotlib import pyplot as plt
import streamlit as st
import joblib
from pathlib import Path
import numpy as np
import pandas as pd
import os
import seaborn as sns
print("Current Working Directory:", os.getcwd())  # Add this line at top


BASE_DIR = Path(__file__).resolve().parent.parent  # This gives you BankEase/
models = {
    "Logistic Regression": joblib.load(BASE_DIR / "backend/models/logistic_model.pkl"),
    "Random Forest": joblib.load(BASE_DIR / "backend/models/rf_model.pkl"),
    "XGBoost": joblib.load(BASE_DIR / "backend/models/xgb_model.pkl")
}

scaler = joblib.load(BASE_DIR / "backend/models/scaler.pkl")


st.set_page_config(page_title="BankEase Fraud Detection", layout="wide")

# Sidebar
st.sidebar.markdown("## Navigation")
st.sidebar.info("Use this app to test transactions for potential fraud.")
st.sidebar.markdown("---")

# Title
st.markdown("<h1 style='color: #2E86C1;'>💳 BankEase Fraud Detection System</h1>", unsafe_allow_html=True)
st.write("Welcome to the interactive fraud detection system. Fill in the transaction details below and select a model to predict whether it's fraudulent or not.")

with st.form("fraud_form"):
    from_account = st.number_input("From Account ID", min_value=1, step=1)
    to_account = st.number_input("To Account ID", min_value=1, step=1)
    amount = st.number_input("Transaction Amount ($)", min_value=0.01, step=0.01)
    hour = st.slider("Transaction Hour", 0, 23)
    day_name = st.selectbox("Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    dayofweek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day_name)
    model_name = st.selectbox("Choose Model", options=list(models.keys()))
    submitted = st.form_submit_button("🚀 Predict")

# 🚦 Prediction Logic
if submitted:
    input_df = pd.DataFrame([{
        "from_account": from_account,
        "to_account": to_account,
        "amount": amount,
        "hour": hour,
        "dayofweek": dayofweek
    }])

    scaled = scaler.transform(input_df)
    model = models[model_name]
    prediction = model.predict(scaled)[0]

    st.success(f"✅ Model: {model_name}")
    if prediction:
        st.error("🚨 Yes, this is likely a fraudulent transaction.")
    else:
        st.success("✅ No, transaction seems legitimate.")
            
st.markdown("### 🔍 Dataset Insight (Simulated)")

# Optional: Simulate basic dataset for demo chart
fraud_count = 124
legit_count = 876

fig, ax = plt.subplots()
ax.pie([fraud_count, legit_count], labels=["Fraud", "Legit"], autopct="%1.1f%%", colors=["#E74C3C", "#2ECC71"])
st.pyplot(fig)
