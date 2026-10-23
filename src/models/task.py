from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    QUEUED = "queued"
    RESEARCHING = "researching"
    QUALIFYING = "qualifying"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"

class ApprovalAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"

class ApprovalDecision(BaseModel):
    action: ApprovalAction
    feedback: Optional[str] = None
    edited_draft: Optional[str] = None

class AgentTask(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.QUEUED
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
