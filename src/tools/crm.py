import hashlib
from typing import Any


class DemoCRMConnector:
    """Local integration boundary. It records intent and never calls an external service."""

    def __init__(self) -> None:
        self.audit_log: list[dict[str, Any]] = []

    async def sync_lead(self, email: str, properties: dict[str, Any]) -> dict[str, Any]:
        record_id = hashlib.sha256(email.encode()).hexdigest()[:12]
        event = {
            "crm_id": f"demo_{record_id}",
            "email": email,
            "status": "recorded",
            "mode": "demo",
            "properties": properties,
        }
        self.audit_log.append(event)
        return event

    async def queue_follow_up(self, email: str, body: str) -> dict[str, Any]:
        event = {
            "status": "queued_for_demo",
            "recipient": email,
            "body_length": len(body),
            "mode": "demo",
        }
        self.audit_log.append(event)
        return event
