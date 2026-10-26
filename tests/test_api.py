from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_lead_ingestion_and_pending_review_flow():
    response = client.post(
        "/api/v1/leads/process",
        json={
            "name": "Jordan Smith",
            "email": "jordan@example.com",
            "company_name": "Example Education Group",
            "website": "https://example.com",
            "company_size": "enterprise",
            "contact_role": "Founder",
            "inquiry_message": "This is blocking our team and we need an urgent workflow automation plan.",
        },
    )
    assert response.status_code == 202
    task = response.json()
    assert task["status"] == "waiting_approval"

    pending = client.get("/api/v1/tasks/pending-approvals")
    assert pending.status_code == 200
    assert task["task_id"] in {item["task_id"] for item in pending.json()}

    fetched = client.get(f"/api/v1/tasks/{task['task_id']}")
    assert fetched.status_code == 200


def test_input_validation_rejects_bad_email_and_website():
    response = client.post(
        "/api/v1/leads/process",
        json={
            "name": "A",
            "email": "not-an-email",
            "company_name": "Example",
            "website": "javascript:alert(1)",
        },
    )
    assert response.status_code == 422
