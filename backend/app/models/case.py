# BIIP-SIH2026 Case Model
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import uuid


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


class CheckpointType(str, Enum):
    AIRPORT = "AIRPORT"
    SEA_PORT = "SEA_PORT"
    LAND_BORDER = "LAND_BORDER"
    RAIL = "RAIL"


class Case(SQLModel, table=True):
    __tablename__ = "cases"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_number: str = Field(unique=True, index=True)
    status: CaseStatus = Field(default=CaseStatus.CREATED, index=True)
    recommendation: Optional[RecommendationType] = Field(default=None, index=True)
    recommendation_confidence: Optional[float] = Field(default=None)
    recommendation_reasoning: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    officer_id: Optional[str] = Field(default=None, index=True)
    is_offline: bool = Field(default=False)
    metadata_json: Optional[str] = Field(default=None)

    # Relationships
    person: Optional["Person"] = Relationship(back_populates="case", sa_relationship_kwargs={"uselist": False})
    documents: List["Document"] = Relationship(back_populates="case")
    face_results: List["FaceResult"] = Relationship(back_populates="case")
    tamper_results: List["TamperResult"] = Relationship(back_populates="case")
    evidence_atoms: List["EvidenceAtom"] = Relationship(back_populates="case")
    identity_nodes: List["IdentityNode"] = Relationship(back_populates="case")
    audit_events: List["AuditEvent"] = Relationship(back_populates="case")
    officer_actions: List["OfficerAction"] = Relationship(back_populates="case")
    audit_log: List["AuditLog"] = Relationship(back_populates="case")