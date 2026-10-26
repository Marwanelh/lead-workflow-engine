import pytest

from src.agent.orchestrator import LeadWorkflowService
from src.models.lead import CompanySize, LeadInput, LeadTier
from src.models.task import ApprovalAction, ApprovalDecision, TaskStatus
from src.storage.database import InMemoryTaskRepository


def enterprise_lead() -> LeadInput:
    return LeadInput(
        name="Alex Mercer",
        email="alex@example.com",
        company_name="Example Systems",
        website="https://example.com",
        company_size=CompanySize.ENTERPRISE,
        contact_role="Operations Director",
        inquiry_message="Our admissions workflow is blocking response times and needs an urgent automation review.",
    )


@pytest.mark.asyncio
async def test_high_priority_lead_waits_for_human_approval():
    service = LeadWorkflowService(InMemoryTaskRepository())

    task = await service.start_pipeline(enterprise_lead())

    assert task.status == TaskStatus.WAITING_APPROVAL
    assert task.result["scorecard"]["tier"] == LeadTier.HIGH_PRIORITY
    assert task.result["requires_human_approval"] is True
    assert "30+" not in task.result["drafted_response"]


@pytest.mark.asyncio
async def test_approval_records_demo_integrations_without_network_calls():
    service = LeadWorkflowService(InMemoryTaskRepository())
    task = await service.start_pipeline(enterprise_lead())

    resolved = await service.resolve_approval(
        task.task_id, ApprovalDecision(action=ApprovalAction.APPROVE)
    )

    assert resolved.status == TaskStatus.COMPLETED
    assert resolved.result["crm_sync"]["mode"] == "demo"
    assert resolved.result["follow_up"]["status"] == "queued_for_demo"


@pytest.mark.asyncio
async def test_modify_requires_an_edited_draft():
    service = LeadWorkflowService(InMemoryTaskRepository())
    task = await service.start_pipeline(enterprise_lead())

    with pytest.raises(ValueError, match="edited_draft"):
        await service.resolve_approval(
            task.task_id, ApprovalDecision(action=ApprovalAction.MODIFY)
        )


@pytest.mark.asyncio
async def test_incomplete_lead_is_nurtured_without_outreach():
    service = LeadWorkflowService(InMemoryTaskRepository())
    lead = LeadInput(
        name="Sam Lee",
        email="sam@example.com",
        company_name="Example Studio",
    )

    task = await service.start_pipeline(lead)

    assert task.status == TaskStatus.COMPLETED
    assert task.result["scorecard"]["tier"] == LeadTier.NURTURE
    assert set(task.result["scorecard"]["missing_information"]) == {
        "company_size",
        "contact_role",
        "inquiry_message",
    }
    assert "crm_sync" not in task.result
