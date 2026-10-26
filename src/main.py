import uvicorn
from fastapi import FastAPI, HTTPException, status

from .agent.orchestrator import LeadWorkflowService
from .models.lead import LeadInput
from .models.task import AgentTask, ApprovalDecision
from .storage.database import InMemoryTaskRepository

app = FastAPI(
    title="Lead Workflow Engine",
    description="A runnable reference implementation for lead qualification, routing, and human review.",
    version="2.0.0",
)

repo = InMemoryTaskRepository()
workflow = LeadWorkflowService(repo)


@app.get("/health", tags=["monitoring"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "lead-workflow-engine"}


@app.post(
    "/api/v1/leads/process",
    response_model=AgentTask,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["workflow"],
)
async def process_lead(lead: LeadInput) -> AgentTask:
    return await workflow.start_pipeline(lead)


@app.get(
    "/api/v1/tasks/pending-approvals",
    response_model=list[AgentTask],
    tags=["human review"],
)
async def list_pending_approvals() -> list[AgentTask]:
    return await repo.list_pending_approvals()


@app.get("/api/v1/tasks/{task_id}", response_model=AgentTask, tags=["workflow"])
async def get_task_status(task_id: str) -> AgentTask:
    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post(
    "/api/v1/tasks/{task_id}/decision",
    response_model=AgentTask,
    tags=["human review"],
)
async def submit_human_decision(task_id: str, decision: ApprovalDecision) -> AgentTask:
    try:
        return await workflow.resolve_approval(task_id, decision)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000)
