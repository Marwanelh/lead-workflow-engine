import uuid

from ..models.lead import (
    CompanySize,
    LeadInput,
    LeadTier,
    LeadWorkflowState,
    QualificationScorecard,
)
from ..models.task import AgentTask, ApprovalAction, ApprovalDecision, TaskStatus
from ..storage.database import InMemoryTaskRepository
from ..tools.crm import DemoCRMConnector


class LeadWorkflowService:
    """Runs a deterministic lead workflow with an explicit human approval gate."""

    def __init__(self, repository: InMemoryTaskRepository) -> None:
        self.repo = repository
        self.crm = DemoCRMConnector()

    async def start_pipeline(self, lead: LeadInput) -> AgentTask:
        task = AgentTask(
            task_id=f"task_{uuid.uuid4().hex[:10]}",
            status=TaskStatus.QUEUED,
            payload=lead.model_dump(),
        )
        await self.repo.save_task(task)

        task.status = TaskStatus.QUALIFYING
        await self.repo.save_task(task)

        state = self._build_state(lead)
        task.result = state.model_dump()
        task.status = (
            TaskStatus.WAITING_APPROVAL
            if state.requires_human_approval
            else TaskStatus.COMPLETED
        )
        await self.repo.save_task(task)
        return task

    def _build_state(self, lead: LeadInput) -> LeadWorkflowState:
        budget_scores = {
            CompanySize.ENTERPRISE: 90,
            CompanySize.MID_MARKET: 75,
            CompanySize.SMALL: 55,
            CompanySize.UNKNOWN: 45,
        }
        budget_fit = budget_scores[lead.company_size]

        role = (lead.contact_role or "").lower()
        decision_maker_terms = ("founder", "owner", "ceo", "cto", "director", "head")
        authority_fit = 90 if any(term in role for term in decision_maker_terms) else 60 if role else 40

        message = (lead.inquiry_message or "").strip()
        urgent_terms = ("urgent", "immediately", "deadline", "blocking", "asap")
        need_urgency = 90 if any(term in message.lower() for term in urgent_terms) else 70 if len(message) >= 80 else 55 if message else 30

        composite = round(budget_fit * 0.35 + authority_fit * 0.30 + need_urgency * 0.35, 1)
        tier = LeadTier.HIGH_PRIORITY if composite >= 80 else LeadTier.QUALIFIED if composite >= 60 else LeadTier.NURTURE

        evidence = [f"Company size supplied as {lead.company_size.value}."]
        if lead.contact_role:
            evidence.append(f"Contact role supplied as {lead.contact_role}.")
        if message:
            evidence.append("An inbound need statement was provided.")

        missing = []
        if lead.company_size == CompanySize.UNKNOWN:
            missing.append("company_size")
        if not lead.contact_role:
            missing.append("contact_role")
        if not message:
            missing.append("inquiry_message")

        requires_approval = tier in (LeadTier.HIGH_PRIORITY, LeadTier.QUALIFIED)
        drafted_response = (
            f"Hi {lead.name},\n\n"
            f"Thank you for contacting us about {lead.company_name}'s workflow needs. "
            "A team member will review the details and follow up with relevant next steps."
        )

        return LeadWorkflowState(
            lead=lead,
            scorecard=QualificationScorecard(
                budget_fit=budget_fit,
                authority_fit=authority_fit,
                need_urgency=need_urgency,
                composite_score=composite,
                tier=tier,
                evidence=evidence,
                missing_information=missing,
            ),
            drafted_response=drafted_response,
            requires_human_approval=requires_approval,
            approval_status="waiting_review" if requires_approval else "not_required",
        )

    async def resolve_approval(self, task_id: str, decision: ApprovalDecision) -> AgentTask:
        task = await self.repo.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task.status != TaskStatus.WAITING_APPROVAL:
            raise ValueError(f"Task {task_id} is not awaiting approval")

        state = LeadWorkflowState.model_validate(task.result)
        if decision.action == ApprovalAction.REJECT:
            state.approval_status = "rejected"
            task.result = state.model_dump()
            task.status = TaskStatus.REJECTED
            await self.repo.save_task(task)
            return task

        if decision.action == ApprovalAction.MODIFY:
            if not decision.edited_draft:
                raise ValueError("edited_draft is required for a modify decision")
            state.drafted_response = decision.edited_draft
            state.approval_status = "modified_and_approved"
        else:
            state.approval_status = "approved"

        crm_result = await self.crm.sync_lead(
            state.lead.email,
            {
                "tier": state.scorecard.tier.value,
                "score": state.scorecard.composite_score,
            },
        )
        follow_up_result = await self.crm.queue_follow_up(
            state.lead.email, state.drafted_response
        )
        result = state.model_dump()
        result["crm_sync"] = crm_result
        result["follow_up"] = follow_up_result
        task.result = result
        task.status = TaskStatus.COMPLETED
        await self.repo.save_task(task)
        return task
