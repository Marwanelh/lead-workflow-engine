import logging
import uuid
from typing import Dict, Any, Optional
from ..models.lead import (
    LeadInput,
    AgentLeadState,
    QualificationScorecard,
    LeadTier
)
from ..models.task import AgentTask, TaskStatus, ApprovalDecision, ApprovalAction
from ..tools.mcp_client import MCPToolProvider
from ..tools.crm import CRMConnector
from ..storage.database import InMemoryTaskRepository

logger = logging.getLogger(__name__)

class LeadAgentOrchestrator:
    """
    Core Autonomous Agent orchestrating lead research, qualification, and routing.
    Enforces deterministic state transitions, schema validation, and HITL safety gates.
    """
    def __init__(self, repository: InMemoryTaskRepository):
        self.repo = repository
        self.mcp = MCPToolProvider()
        self.crm = CRMConnector()

    async def start_pipeline(self, lead_input: LeadInput) -> AgentTask:
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        task = AgentTask(
            task_id=task_id,
            status=TaskStatus.QUEUED,
            payload=lead_input.model_dump()
        )
        await self.repo.save_task(task)

        # Execute pipeline asynchronously
        await self._run_pipeline(task, lead_input)
        return task

    async def _run_pipeline(self, task: AgentTask, lead: LeadInput) -> None:
        try:
            task.status = TaskStatus.RESEARCHING
            await self.repo.save_task(task)
            intelligence = await self.mcp.search_company_profile(lead.company_name, lead.website or "")

            task.status = TaskStatus.QUALIFYING
            await self.repo.save_task(task)

            # Deterministic scoring model
            budget_fit = 85 if "AI" in lead.company_name or "Cloud" in lead.company_name else 70
            authority_fit = 90 if any(role in (lead.inquiry_message or "").lower() for role in ["founder", "ceo", "director", "head"]) else 75
            need_urgency = 88 if lead.inquiry_message and len(lead.inquiry_message) > 40 else 65

            composite = (budget_fit * 0.4) + (authority_fit * 0.3) + (need_urgency * 0.3)
            
            if composite >= 80:
                tier = LeadTier.TIER_1_ENTERPRISE
            elif composite >= 65:
                tier = LeadTier.TIER_2_MID_MARKET
            else:
                tier = LeadTier.TIER_3_NURTURE

            scorecard = QualificationScorecard(
                budget_fit=budget_fit,
                authority_fit=authority_fit,
                need_urgency=need_urgency,
                composite_score=round(composite, 1),
                tier=tier,
                key_reasons=[
                    f"Identified {len(intelligence.technologies_used)} core modern stack components",
                    f"Strong ICP signals: {', '.join(intelligence.signals[:2])}"
                ],
                suggested_angle=f"Focus on automated {intelligence.industry} workflows with verified ROI."
            )

            confidence = 0.92 if lead.website else 0.82
            requires_hitl = (confidence < 0.85) or (tier == LeadTier.TIER_1_ENTERPRISE)

            drafted_outreach = (
                f"Hi {lead.name},\n\n"
                f"I noticed {lead.company_name}'s recent initiative to streamline workflows across your {intelligence.industry} operations. "
                f"We recently deployed an automated orchestration engine that eliminated 30+ manual hours weekly for similar teams.\n\n"
                f"Would you be open to reviewing the technical architecture breakdown next Tuesday?"
            )

            state = AgentLeadState(
                lead=lead,
                intelligence=intelligence,
                scorecard=scorecard,
                drafted_response=drafted_outreach,
                confidence_score=confidence,
                requires_human_approval=requires_hitl,
                approval_status="waiting_review" if requires_hitl else "auto_approved"
            )

            if requires_hitl:
                task.status = TaskStatus.WAITING_APPROVAL
                task.result = state.model_dump()
                await self.repo.save_task(task)
                logger.info(f"[HITL Gate] Task {task.task_id} paused for human verification (Tier 1 enterprise lead)")
            else:
                await self._finalize_dispatch(task, state)

        except Exception as e:
            logger.error(f"[Pipeline Error] Task {task.task_id} failed: {str(e)}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error = str(e)
            await self.repo.save_task(task)

    async def resolve_approval(self, task_id: str, decision: ApprovalDecision) -> AgentTask:
        task = await self.repo.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.status != TaskStatus.WAITING_APPROVAL:
            raise ValueError(f"Task {task_id} is in status '{task.status}', not awaiting approval")

        state = AgentLeadState.model_validate(task.result)

        if decision.action == ApprovalAction.REJECT:
            task.status = TaskStatus.REJECTED
            state.approval_status = "rejected"
            task.result = state.model_dump()
            await self.repo.save_task(task)
            return task

        if decision.action == ApprovalAction.MODIFY and decision.edited_draft:
            state.drafted_response = decision.edited_draft
            state.approval_status = "modified_and_approved"
        else:
            state.approval_status = "approved"

        await self._finalize_dispatch(task, state)
        return task

    async def _finalize_dispatch(self, task: AgentTask, state: AgentLeadState) -> None:
        # Sync to CRM
        crm_res = await self.crm.sync_lead(state.lead.email, {
            "tier": state.scorecard.tier if state.scorecard else "Unclassified",
            "score": state.scorecard.composite_score if state.scorecard else 0,
            "status": "Qualified - Ready for Outreach"
        })
        
        # Dispatch outreach
        outreach_res = await self.crm.schedule_outreach(
            state.lead.email, 
            state.drafted_response or ""
        )

        task.status = TaskStatus.COMPLETED
        res = state.model_dump()
        res["crm_sync"] = crm_res
        res["outreach_status"] = outreach_res
        task.result = res
        await self.repo.save_task(task)
        logger.info(f"[Pipeline Complete] Task {task.task_id} fully executed and synchronized")
