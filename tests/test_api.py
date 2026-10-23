import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_lead_ingestion_api():
    payload = {
        "name": "Jordan Belfort",
        "email": "jordan@stratton.com",
        "company_name": "Stratton AI Capital",
        "website": "https://stratton.ai",
        "inquiry_message": "Need automated outbound qualification pipelines."
    }
    res = client.post("/api/v1/leads/process", json=payload)
    assert res.status_code == 202
    data = res.json()
    assert "task_id" in data
    assert data["status"] in ["waiting_approval", "completed"]

def test_pending_approvals_endpoint():
    res = client.get("/api/v1/tasks/pending-approvals")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
