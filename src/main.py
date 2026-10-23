import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

from .models.lead import LeadInput
from .models.task import AgentTask, ApprovalDecision
from .storage.database import InMemoryTaskRepository
from .agent.orchestrator import LeadAgentOrchestrator

app = FastAPI(
    title="Autonomous Lead Agent & Workflow Engine",
    description="Production-grade AI agent with MCP tool execution, structured Pydantic outputs, and Human-in-the-Loop review gates.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repo = InMemoryTaskRepository()
orchestrator = LeadAgentOrchestrator(repo)

@app.get("/health", tags=["Monitoring"])
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "autonomous-lead-agent"}

@app.post("/api/v1/leads/process", response_model=AgentTask, status_code=status.HTTP_202_ACCEPTED, tags=["Agent Execution"])
async def process_lead(lead: LeadInput) -> AgentTask:
    """Ingest a new lead, trigger autonomous research, qualification, and routing."""
    return await orchestrator.start_pipeline(lead)

@app.get("/api/v1/tasks/{task_id}", response_model=AgentTask, tags=["Task State"])
async def get_task_status(task_id: str) -> AgentTask:
    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/v1/tasks/pending-approvals", response_model=List[AgentTask], tags=["Human in the Loop"])
async def list_pending_approvals() -> List[AgentTask]:
    """Retrieve all high-stakes tasks awaiting human sign-off."""
    return await repo.list_pending_approvals()

@app.post("/api/v1/tasks/{task_id}/decision", response_model=AgentTask, tags=["Human in the Loop"])
async def submit_human_decision(task_id: str, decision: ApprovalDecision) -> AgentTask:
    """Approve, modify, or reject a pending agent task."""
    try:
        return await orchestrator.resolve_approval(task_id, decision)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
