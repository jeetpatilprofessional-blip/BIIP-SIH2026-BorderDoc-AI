# BIIP-SIH2026 Evidence Schemas
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import json


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


class EvidenceAtomRead(BaseModel):
    id: str
    case_id: str
    evidence_type: str
    source: EvidenceSource
    severity: EvidenceSeverity
    confidence: float
    description: str
    explanation: Optional[str] = None
    entities: Optional[List[str]] = None
    freshness: FreshnessState
    last_synced_at: Optional[datetime] = None
    freshness_policy_hours: Optional[int] = None
    rule_or_model_version: Optional[str] = None
    created_at: datetime

    @field_validator('entities', mode='before')
    @classmethod
    def parse_entities(cls, v: Any) -> Optional[List[str]]:
        """Parse entities from JSON string if needed"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [v]  # fallback: treat as single entity
        if isinstance(v, list):
            return v
        return [str(v)]

    class Config:
        from_attributes = True


class EvidenceSummary(BaseModel):
    total: int
    by_severity: dict
    by_source: dict
    by_freshness: dict
    critical_count: int
    high_count: int
    stale_count: int
    unavailable_count: int