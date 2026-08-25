# BIIP-SIH2026 Evidence Models
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid


class EvidenceSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceSource(str, Enum):
    OCR = "OCR"
    MRZ = "MRZ"
    BARCODE = "BARCODE"
    NFC = "NFC"
    DOCUMENT_VALIDATION = "DOCUMENT_VALIDATION"
    TAMPER_ANALYSIS = "TAMPER_ANALYSIS"
    FACE_VERIFICATION = "FACE_VERIFICATION"
    LIVENESS = "LIVENESS"
    IDENTITY_GRAPH = "IDENTITY_GRAPH"
    VISA_RULES = "VISA_RULES"
    PERMIT_RULES = "PERMIT_RULES"
    TRAVEL_CHRONOLOGY = "TRAVEL_CHRONOLOGY"
    WATCHLIST = "WATCHLIST"
    REVOCATION = "REVOCATION"
    FRESHNESS = "FRESHNESS"
    OFFICER = "OFFICER"


class FreshnessState(str, Enum):
    VERIFIED_FRESH = "VERIFIED_FRESH"
    VERIFIED_STALE = "VERIFIED_STALE"
    UNAVAILABLE = "UNAVAILABLE"
    CONFIRMED_ADVERSE = "CONFIRMED_ADVERSE"


class EvidenceAtom(SQLModel, table=True):
    __tablename__ = "evidence_atoms"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)

    # Evidence identification
    evidence_type: str = Field(index=True)  # e.g., "DOB_MISMATCH", "FACE_MATCH"
    source: EvidenceSource = Field(index=True)
    severity: EvidenceSeverity = Field(index=True)
    confidence: float = Field(default=0.0)

    # Description
    description: str
    explanation: Optional[str] = Field(default=None)

    # Entities involved (document IDs, person IDs, etc.)
    entities: Optional[str] = Field(default=None)  # JSON array

    # Freshness
    freshness: FreshnessState = Field(default=FreshnessState.VERIFIED_FRESH)
    last_synced_at: Optional[datetime] = Field(default=None)
    freshness_policy_hours: Optional[int] = Field(default=None)

    # Version tracking
    rule_or_model_version: Optional[str] = Field(default=None)

    # Signature for integrity (simplified for prototype)
    signature: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="evidence_atoms")