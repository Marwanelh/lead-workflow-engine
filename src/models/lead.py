from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

class LeadTier(str, Enum):
    TIER_1_ENTERPRISE = "Tier 1 - High Priority"
    TIER_2_MID_MARKET = "Tier 2 - Qualified"
    TIER_3_NURTURE = "Tier 3 - Nurture"
    DISQUALIFIED = "Disqualified"

class LeadInput(BaseModel):
    name: str = Field(..., description="Full contact name")
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="Business email address")
    company_name: str = Field(..., description="Target company name")
    website: Optional[str] = Field(None, description="Company website URL")
    inquiry_message: Optional[str] = Field(None, description="Initial inbound message or intent")

class CompanyIntelligence(BaseModel):
    domain: str
    industry: str
    estimated_size: str
    technologies_used: List[str] = Field(default_factory=list)
    signals: List[str] = Field(default_factory=list)

class QualificationScorecard(BaseModel):
    budget_fit: int = Field(..., ge=0, le=100, description="Estimated budget alignment score")
    authority_fit: int = Field(..., ge=0, le=100, description="Decision-maker seniority score")
    need_urgency: int = Field(..., ge=0, le=100, description="Problem urgency score")
    composite_score: float = Field(..., ge=0.0, le=100.0)
    tier: LeadTier
    key_reasons: List[str]
    suggested_angle: str

class AgentLeadState(BaseModel):
    lead: LeadInput
    intelligence: Optional[CompanyIntelligence] = None
    scorecard: Optional[QualificationScorecard] = None
    drafted_response: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_human_approval: bool = False
    approval_status: str = "pending"
