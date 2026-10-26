from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CompanySize(str, Enum):
    SMALL = "small"
    MID_MARKET = "mid_market"
    ENTERPRISE = "enterprise"
    UNKNOWN = "unknown"


class LeadTier(str, Enum):
    HIGH_PRIORITY = "high_priority"
    QUALIFIED = "qualified"
    NURTURE = "nurture"


class LeadInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    company_name: str = Field(min_length=2, max_length=150)
    website: Optional[str] = Field(default=None, pattern=r"^https?://[^\s]+$")
    company_size: CompanySize = CompanySize.UNKNOWN
    contact_role: Optional[str] = Field(default=None, max_length=100)
    inquiry_message: Optional[str] = Field(default=None, max_length=2_000)


class QualificationScorecard(BaseModel):
    budget_fit: int = Field(ge=0, le=100)
    authority_fit: int = Field(ge=0, le=100)
    need_urgency: int = Field(ge=0, le=100)
    composite_score: float = Field(ge=0, le=100)
    tier: LeadTier
    evidence: list[str]
    missing_information: list[str]


class LeadWorkflowState(BaseModel):
    lead: LeadInput
    scorecard: QualificationScorecard
    drafted_response: str
    requires_human_approval: bool
    approval_status: str
