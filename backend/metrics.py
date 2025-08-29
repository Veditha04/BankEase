# backend/metrics.py
from prometheus_client import Counter, Histogram, start_http_server

# Label by model family so you can compare xgb vs rf vs lr
PREDICTION_COUNT = Counter(
    "bankease_predictions_total",
    "Total predictions made",
    ["model"],
)

PREDICTION_ERRORS = Counter(
    "bankease_prediction_errors_total",
    "Total prediction errors",
    ["type"],
)

PREDICTION_LATENCY = Histogram(
    "bankease_prediction_latency_seconds",
    "Prediction latency in seconds",
    ["model"],
)

def setup_metrics(port: int = 9100):
    """
    Starts a tiny HTTP server that exposes metrics at http://localhost:<port>/
    Keep this bound to localhost in dev.
    """
    start_http_server(port)
