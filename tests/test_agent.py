import pytest
from src.models.lead import LeadInput, LeadTier
from src.models.task import TaskStatus, ApprovalDecision, ApprovalAction
from src.storage.database import InMemoryTaskRepository
from src.agent.orchestrator import LeadAgentOrchestrator

@pytest.mark.asyncio
async def test_lead_pipeline_tier1_hits_approval_gate():
    repo = InMemoryTaskRepository()
    orchestrator = LeadAgentOrchestrator(repo)

    lead = LeadInput(
        name="Alex Mercer",
        email="alex@ai-enterprises.com",
        company_name="AI Global Systems",
        website="https://aiglobalsystems.com",
        inquiry_message="Looking to integrate an autonomous orchestration layer for our sales engineering team."
    )

    task = await orchestrator.start_pipeline(lead)

    assert task.status == TaskStatus.WAITING_APPROVAL
    assert task.result is not None
    assert task.result["scorecard"]["tier"] == LeadTier.TIER_1_ENTERPRISE
    assert task.result["requires_human_approval"] is True

@pytest.mark.asyncio
async def test_human_approval_resolution():
    repo = InMemoryTaskRepository()
    orchestrator = LeadAgentOrchestrator(repo)

    lead = LeadInput(
        name="Sarah Connor",
        email="sarah@skynet.com",
        company_name="Cyberdyne AI Systems",
        website="https://cyberdyne.ai",
        inquiry_message="Urgent workflow modernization needed."
    )

    task = await orchestrator.start_pipeline(lead)
    assert task.status == TaskStatus.WAITING_APPROVAL

    decision = ApprovalDecision(
        action=ApprovalAction.APPROVE,
        feedback="Verified legitimacy of enterprise inquiry."
    )

    resolved = await orchestrator.resolve_approval(task.task_id, decision)
    assert resolved.status == TaskStatus.COMPLETED
    assert resolved.result["crm_sync"]["status"] == "synchronized"
    assert resolved.result["outreach_status"]["status"] == "queued"
