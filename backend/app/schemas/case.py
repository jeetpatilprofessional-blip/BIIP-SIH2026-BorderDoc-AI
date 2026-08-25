# BIIP-SIH2026 Case Schemas
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class CaseStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class RecommendationType(str, Enum):
    LOW_CONCERN = "LOW_CONCERN"
    SECONDARY_INSPECTION = "SECONDARY_INSPECTION"
    HIGH_CONCERN = "HIGH_CONCERN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CaseCreate(BaseModel):
    officer_id: Optional[str] = None
    metadata: Optional[dict] = None


class CaseRead(BaseModel):
    id: str
    case_number: str
    status: CaseStatus
    recommendation: Optional[RecommendationType] = None
    recommendation_confidence: Optional[float] = None
    recommendation_reasoning: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    officer_id: Optional[str] = None
    is_offline: bool = False

    class Config:
        from_attributes = True


class CaseList(BaseModel):
    cases: List[CaseRead]
    total: int
    page: int
    page_size: int


class CaseUpdate(BaseModel):
    status: Optional[CaseStatus] = None
    officer_id: Optional[str] = None
    metadata: Optional[dict] = None