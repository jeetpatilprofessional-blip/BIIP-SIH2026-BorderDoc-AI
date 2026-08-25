# BIIP-SIH2026 Officer Action Model
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid


class OfficerActionType(str, Enum):
    CLEAR = "CLEAR"
    SECONDARY_INSPECTION = "SECONDARY_INSPECTION"
    ESCALATE = "ESCALATE"
    DETAIN = "DETAIN"
    REFUSE_ENTRY = "REFUSE_ENTRY"
    REQUEST_DOCUMENTS = "REQUEST_DOCUMENTS"
    OTHER = "OTHER"


class OfficerAction(SQLModel, table=True):
    __tablename__ = "officer_actions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)

    action: OfficerActionType = Field(index=True)
    reason: str

    # AI recommendation at time of decision
    ai_recommendation: Optional[str] = Field(default=None)  # RecommendationType
    ai_confidence: Optional[float] = Field(default=None)

    # Officer identification (simplified for prototype)
    officer_id: Optional[str] = Field(default=None)
    officer_name: Optional[str] = Field(default=None)

    # Additional context
    notes: Optional[str] = Field(default=None)
    extra_data: Optional[str] = Field(default=None, alias="metadata")  # JSON

    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="officer_actions")