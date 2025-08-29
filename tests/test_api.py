# tests/test_api.py
import os
import sys
import pytest

# --- make imports work without changing your code ---
HERE = os.path.abspath(os.path.dirname(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(HERE, "..", "backend"))

# Add backend/ to import path and chdir so "from api import api_bp" works
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from app import app  # imports your existing backend/app.py

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_root_health(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json() == {"message": "BankEase DB Connected!"}

def test_404_handler(client):
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["error"] == "Resource not found"
    assert body["status_code"] == 404

def test_protected_without_token(client):
    resp = client.get("/protected")
    assert resp.status_code == 401  # missing JWT → unauthorized

def test_api_status(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "API is running"}
