# streamlit_app/fraud_ui.py
import time
import json
import requests
import pandas as pd
import streamlit as st

# ----- Configuration -----
# You can override API_BASE by creating .streamlit/secrets.toml with:
# API_BASE = "http://localhost:5050/api"
API_BASE = st.secrets.get("API_BASE", "http://localhost:5050/api")

st.set_page_config(page_title="BankEase – Fraud Screening", layout="centered")

# ==== Custom theme: Aurora (teal + purple), extra pop ====
st.markdown("""
<style>
:root{
  /* palette */
  --accent:#22d3ee;      /* teal */
  --accent2:#a78bfa;     /* purple */

  /* background tones (slightly brighter than before) */
  --bg-top:#08142a;
  --bg-bottom:#0b1220;

  /* surfaces */
  --glass:rgba(255,255,255,.06);
  --border:rgba(255,255,255,.10);
}

/* page background: layered + stronger color mix so it clearly shows */
.stApp{
  background:
    radial-gradient(1100px 560px at 8% -12%, color-mix(in oklab, var(--accent) 32%, transparent), transparent 62%),
    radial-gradient(1000px 520px at 98% -8%, color-mix(in oklab, var(--accent2) 30%, transparent), transparent 64%),
    radial-gradient(900px 500px at 40% 120%, color-mix(in oklab, var(--accent) 18%, transparent), transparent 70%),
    linear-gradient(180deg, var(--bg-top), var(--bg-bottom));
}

/* keep header transparent */
[data-testid="stHeader"]{ background:transparent }

/* sidebar: glass + subtle border */
section[data-testid="stSidebar"]{
  background: linear-gradient(180deg, var(--glass), rgba(255,255,255,.03));
  border-right: 1px solid var(--border);
}

/* buttons: vivid gradient + slight hover lift */
div.stButton>button{
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  color:#0b1220; border:0; border-radius:12px; font-weight:600;
  box-shadow: 0 6px 18px color-mix(in oklab, var(--accent) 18%, transparent);
}
div.stButton>button:hover{ filter:brightness(1.08); transform: translateY(-1px); }

/* inputs: rounded + tinted */
.stNumberInput, .stSelectbox, .stTextInput{
  border-radius:12px !important;
  border:1px solid var(--border) !important;
  background: rgba(255,255,255,.03) !important;
}

/* expander: glass card */
div[data-testid="stExpander"]{
  background: var(--glass);
  border:1px solid var(--border);
  border-radius:12px;
}

/* progress bar: accent gradient, thicker track */
.stProgress > div > div{
  background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;
  height: 12px !important;
  border-radius: 999px !important;
}

/* slider handle ring in accent */
[data-testid="stSlider"] [role="slider"]{
  outline:none !important;
  box-shadow: 0 0 0 4px color-mix(in oklab, var(--accent) 40%, transparent) !important;
}
</style>
""", unsafe_allow_html=True)


# ===== Header =====
st.title("BankEase – Transaction Screening")
st.caption("Enter a transaction to estimate fraud likelihood.")

# ===== Helpers =====
@st.cache_data(ttl=15)
def get_status():
    try:
        r = requests.get(f"{API_BASE.rsplit('/api', 1)[0]}/api/status", timeout=5)
        return r.json()
    except Exception:
        return {}
# ---- Auth token (JWT) + Login UI ----
DEFAULT_TOKEN = st.secrets.get("API_TOKEN", "")
st.sidebar.subheader("Authentication")

# token box (prefilled from secrets if present)

st.sidebar.text_input(
    "API Token (JWT)",
    key="API_TOKEN",
    type="password",
    value=st.secrets.get("API_TOKEN", ""),
    help="Paste a token, or use the login form below."
)

def HEADERS():
    tok = st.session_state.get("AUTH_TOKEN") or st.session_state.get("API_TOKEN") or ""
    return {"Authorization": f"Bearer {tok}"} if tok else {}


# --- Login form (calls /login) ---
with st.sidebar.form("login_form", clear_on_submit=False):
    u = st.text_input("Username", key="LOGIN_USERNAME",
                      value=st.secrets.get("LOGIN_USERNAME", "john_doe"))
    p = st.text_input("Password", type="password", key="LOGIN_PASSWORD",
                      value=st.secrets.get("LOGIN_PASSWORD", "test123"))
    do_login = st.form_submit_button("Login")

if do_login:
    base = API_BASE.rsplit("/api", 1)[0]
    try:
        r = requests.post(f"{base}/login", json={"username": u, "password": p}, timeout=6)
        if r.ok:
            tok = r.json().get("access_token", "")
            if tok:
                st.session_state["AUTH_TOKEN"] = tok
                st.success("Logged in. Token stored in session.")
            else:
                st.error("Login succeeded but no token returned.")
        else:
            # show server message if available
            try:
                msg = r.json().get("error") or r.text
            except Exception:
                msg = r.text
            st.error(f"Login failed ({r.status_code}): {msg}")
    except requests.exceptions.RequestException as e:
        st.error(f"Login error: {e}")

# --- Who am I? + Logout ---
if st.session_state.get("API_TOKEN"):
    base = API_BASE.rsplit("/api", 1)[0]
    try:
        me = requests.get(f"{base}/protected", headers=HEADERS(), timeout=4)
        if me.ok:
            who = me.json().get("logged_in_as")
            st.sidebar.success(f"Logged in as user_id: {who}")
        else:
            st.sidebar.warning("Token present but /protected failed; try re-login.")
    except Exception:
        st.sidebar.warning("Could not reach /protected.")
    if st.sidebar.button("Logout"):
        for k in ("API_TOKEN", "LOGIN_USERNAME", "LOGIN_PASSWORD"):
            st.session_state.pop(k, None)
        st.experimental_rerun()
else:
    st.sidebar.info("Not authenticated. Login or paste a JWT.")

def call_api(payload: dict):
    """Resilient API call with latency measurement and friendly errors."""
    url = f"{API_BASE}/predict"
    try:
        t0 = time.perf_counter()
        r = requests.post(url, json=payload, timeout=8, headers=HEADERS())
        ms = int((time.perf_counter() - t0) * 1000)

        if r.ok:
            out = r.json()
            out["latency_ms"] = out.get("latency_ms", ms)
            return out, None

        # ---------- Friendly error mapping ----------
        # Try to extract a server-provided message
        err_body = None
        try:
            j = r.json()
            err_body = j.get("error") or j.get("msg") or j
        except Exception:
            err_body = r.text or "Unknown error"

        # Auth problems (JWT missing/invalid/expired)
        if r.status_code in (401, 403, 422):
            # Flask-JWT-Extended often returns 401 or 422 with 'msg'
            # Normalize to a single helpful prompt for the user.
            return None, (
                f"Unauthorized ({r.status_code}): {err_body}. "
                "Paste a valid JWT in the left sidebar (get one from /login)."
            )

        # Validation problems from our API (e.g., out-of-range inputs)
        if r.status_code == 400:
            return None, f"Invalid input: {err_body}"

        # Anything else
        return None, f"HTTP {r.status_code}: {err_body}"

    except requests.exceptions.Timeout:
        return None, "Backend timed out. Try again or reduce load."
    except requests.exceptions.ConnectionError:
        return None, "Backend unavailable (connection error). Is the API running?"
    except requests.exceptions.RequestException as e:
        return None, f"Network error contacting API: {e}"

    

# Pretty % readout + single gradient bar (no duplicate track)
def show_probability(prob: float, *, height: int = 12):
    p = max(0.0, min(float(prob), 1.0))
    pct = p * 100.0
    # label with % number
    st.markdown(f"<div style='margin:4px 0 6px 0;opacity:.9'>Fraud probability: "
                f"<strong>{pct:.2f}%</strong></div>", unsafe_allow_html=True)
    # one clean bar
    st.markdown(f"""
    <div style="
        height:{height}px;
        background:rgba(255,255,255,.06);
        border:1px solid var(--border);
        border-radius:999px;
        overflow:hidden;">
      <div style="
          height:100%;
          width:{pct:.2f}%;
          background:linear-gradient(90deg, var(--accent), var(--accent2));
      "></div>
    </div>
    """, unsafe_allow_html=True)

# ===== Sidebar: model pointers + threshold =====
st.sidebar.subheader("Model registry")
_status = get_status()
_models = _status.get("models", {}) if isinstance(_status, dict) else {}
for fam in ["xgb", "rf", "lr"]:
    info = _models.get(fam)
    if info:
        st.sidebar.write(f"**{fam}** → {info.get('version', '?')}")

# pull constraints from any model (they're the same across families)
_any = next((v for v in _models.values() if isinstance(v, dict)), {})
CONS = _any.get("constraints", {}) if _any else {}

def _rng(name, lo=None, hi=None):
    r = CONS.get(name, {})
    return r.get("min", lo), r.get("max", hi)

UID_MIN, UID_MAX = _rng("user_id", 1, 1002)
LOC_MIN, LOC_MAX = _rng("location", 0, 50)
AMT_MIN, _ = _rng("amount", 0.0, None)

# small hint if JWT missing
if not (st.session_state.get("API_TOKEN") or DEFAULT_TOKEN):
    st.info("API is protected. Paste a JWT in the left sidebar (get one from /login).")

threshold = st.sidebar.slider("Decision threshold", 0.05, 0.95, 0.50, 0.01)



# ===== Input form (matches backend contract) =====
# ===== Input form (matches backend contract) =====
with st.form("fraud_form", clear_on_submit=False):
    # two columns for the top row
    c1, c2 = st.columns(2)

    with c1:
        user_id = st.number_input(
            "User ID",
            min_value=int(UID_MIN or 1),
            max_value=int(UID_MAX or 1002),
            value=int(UID_MIN or 1),
            step=1,
            help=f"Valid user ids: {int(UID_MIN or 1)}–{int(UID_MAX or 1002)}."
        )
        dayofweek = st.number_input(
            "Day of Week (0=Mon … 6=Sun)",
            min_value=0, max_value=6, value=2, step=1
        )

    with c2:
        hour = st.number_input(
            "Hour (0–23)",
            min_value=0, max_value=23, value=10, step=1
        )
        model = st.selectbox(
            "Model family",
            options=["xgb", "rf", "lr"], index=0
        )

    # second row (full width) for the numeric fields
    amount = st.number_input(
        "Amount ($)",
        min_value=float(AMT_MIN or 5.01),
        value=max(float(AMT_MIN or 5.01), 99.0),
        step=0.01
    )
    location = st.number_input(
        "Location (encoded)",
        min_value=int(LOC_MIN or 0),
        max_value=int(LOC_MAX or 50),
        value=int(LOC_MIN or 0),
        step=1,
        help=f"Encoded location id: {int(LOC_MIN or 0)}–{int(LOC_MAX or 50)}."
    )

    with st.expander("Advanced (optional)"):
        model_version = st.text_input(
            "Model version",
            value="current",
            help="Use 'current' or a specific saved version like vYYYYMMDD_HHMMSS.",
        )

    submitted = st.form_submit_button("Score transaction")


# ===== Call backend & render =====
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

    # quick client-side clamps (API also validates)
    if not (int(UID_MIN or 0) <= payload["user_id"] <= int(UID_MAX or 10_000)):
        st.error(f"user_id must be between {int(UID_MIN or 0)} and {int(UID_MAX or 10_000)}.")
        st.stop()
    if payload["amount"] < float(AMT_MIN or 0.0):
        st.error(f"amount must be ≥ {float(AMT_MIN or 0.0)}.")
        st.stop()

    with st.spinner("Scoring..."):
        data, err = call_api(payload)

    if err:
        st.error(err)
    else:

        st.session_state.last_payload = payload
        # --- Header metrics
        st.caption(
        f"Model: **{data.get('model_used','?')}** · "
        f"Version: **{data.get('model_version','?')}** · "
        f"Latency: **{data.get('latency_ms','?')} ms**"
)
    
        # --- Probability + decision
        st.subheader("Result")
        prob = float(data.get("probability", 0.0))
        prob_clamped = min(max(prob, 0.0), 1.0)
        show_probability(prob_clamped, height=12)
        decision = "FRAUD" if prob >= threshold else "OK"
        st.write(f"Decision: **{decision}** at p={prob:.3%} (≥ {threshold:.2f})")

        # --- Details (request/response) + cURL + download
        with st.expander("Details (request/response)"):
            st.caption("Request:")
            st.code(json.dumps(payload, indent=2), language="json")
            st.caption("Response:")
            st.code(json.dumps(data, indent=2), language="json")
            curl_lines = [
                f"curl -s -X POST {API_BASE}/predict",
                "  -H 'Content-Type: application/json'",
            ]
            # show the auth header but don't leak the real token
            if st.session_state.get("API_TOKEN"):
                curl_lines.append("  -H 'Authorization: Bearer <JWT>'")
            curl_lines.append(f"  -d '{json.dumps(payload)}'")
            st.caption("cURL:")
            st.code(" \\\n".join(curl_lines), language="bash")

            curl_lines = [
            f"curl -s -X POST {API_BASE}/predict",
             "  -H 'Content-Type: application/json'",
         ]  
# show the auth header but don't leak the real token
            tok_preview = " <JWT>"
            if st.session_state.get("API_TOKEN"):
               curl_lines.append("  -H 'Authorization: Bearer<JWT>'")
               curl_lines.append(f"  -d '{json.dumps(payload)}'")
            st.caption("cURL:")
            st.code(" \\\n".join(curl_lines), language="bash")
            st.download_button(
                "Download response JSON",
                json.dumps(data, indent=2).encode(),
                "response.json",
                "application/json",
            )

        # --- Session history (table + CSV)
        if "history" not in st.session_state:
            st.session_state.history = []
        st.session_state.history.append({
            **payload,
            "probability": round(prob, 6),
            "decision": decision,
            "model_used": data.get("model_used"),
            "model_version": data.get("model_version"),
            "latency_ms": data.get("latency_ms"),
        })
        st.subheader("Recent scores")
        df_hist = pd.DataFrame(st.session_state.history[::-1])  # newest first
        st.dataframe(df_hist, use_container_width=True, height=260)
        st.download_button(
            "Download CSV",
            df_hist.to_csv(index=False).encode(),
            "scores.csv",
            "text/csv",
        )

# ===== Optional extras =====

# Cross-model comparison (lr vs rf vs xgb)
with st.expander("Compare across models"):
    base = st.session_state.get("last_payload")
    if not base:
        st.info("Fill the form and click **Score transaction** once before comparing.")
    else:
        def score_with(model_name: str, data_in: dict):
            r = requests.post(f"{API_BASE}/predict",
                  json={**data_in, "model": model_name, "model_version": "current"},
                  timeout=8, headers=HEADERS())

            r.raise_for_status()
            j = r.json()
            return {"model": model_name,
                    "probability": j.get("probability", 0.0),
                    "latency_ms": j.get("latency_ms")}
        if st.button("Run comparison"):
            rows = [score_with(m, base) for m in ["lr", "rf", "xgb"]]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)


# What-if analysis: vary amount
with st.expander("What-if: vary amount and see risk"):
    base = st.session_state.get("last_payload")
    if not base:
        st.info("Fill the form and click **Score transaction** first.")
    else:
        import numpy as np
        base_amt = float(base["amount"])
        amounts = np.linspace(max(1, base_amt*0.2), base_amt*1.8, 15)
        pts = []
        for a in amounts:
            resp = requests.post(f"{API_BASE}/predict",
                     json={**base, "amount": float(a)},
                     timeout=8, headers=HEADERS())
            if not resp.ok:
            # skip this point if unauthorized/invalid input
               continue
            j = resp.json()

            pts.append((a, j.get("probability", 0.0)))
        chart_df = pd.DataFrame({"amount": [x for x,_ in pts],
                                 "probability": [y for _,y in pts]}).set_index("amount")
        st.line_chart(chart_df)

# Download a valid input CSV template for batch scoring
template_df = pd.DataFrame([
    {"user_id": 1, "amount": 120.50, "location": 3, "hour": 22, "dayofweek": 5},
    {"user_id": 2, "amount": 75.00,  "location": 1, "hour": 14, "dayofweek": 2},
])
st.download_button(
    "Download input CSV template",
    template_df.to_csv(index=False).encode(),
    "bankease_batch_template.csv",
    "text/csv",
)

# Batch CSV scoring
with st.expander("Batch score CSV"):
    uploaded = st.file_uploader("Upload CSV with columns: user_id,amount,location,hour,dayofweek", type=["csv"])
    if uploaded:
        df_in = pd.read_csv(uploaded)
        expected = ["user_id","amount","location","hour","dayofweek"]
        missing = [c for c in expected if c not in df_in.columns]
        if missing:
            st.error(f"Missing columns in CSV: {missing}")
        else:
            out_rows = []
            for _, row in df_in.iterrows():
                req = {k: (int(row[k]) if k=="user_id" else float(row[k])) for k in expected}
                r = requests.post(f"{API_BASE}/predict",
                  json={**req, "model": "xgb", "model_version": "current"},
                  timeout=8, headers=HEADERS())
                if not r.ok:
                   out_rows.append({**req, "error": f"{r.status_code}: {r.text}"})
                   continue
                j = r.json()
                out_rows.append({**req,
                 "probability": j.get("probability"),
                 "prediction": j.get("prediction"),
                 "model": j.get("model_used"),
                 "version": j.get("model_version")})
            df_out = pd.DataFrame(out_rows)
            st.success(f"Scored {len(df_out)} rows.")
            st.dataframe(df_out, use_container_width=True, height=260)
            st.download_button("Download scored CSV",
                               df_out.to_csv(index=False).encode(),
                               "scored.csv", "text/csv")
