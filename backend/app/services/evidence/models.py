# BIIP-SIH2026 Evidence Fusion Models
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class RecommendationType(str, Enum):
    LOW_CONCERN = "LOW_CONCERN"
    SECONDARY_INSPECTION = "SECONDARY_INSPECTION"
    HIGH_CONCERN = "HIGH_CONCERN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FreshnessState(str, Enum):
    VERIFIED_FRESH = "VERIFIED_FRESH"
    VERIFIED_STALE = "VERIFIED_STALE"
    UNAVAILABLE = "UNAVAILABLE"
    CONFIRMED_ADVERSE = "CONFIRMED_ADVERSE"


class EvidenceContribution(BaseModel):
    """A single evidence contribution to the fusion result"""
    evidence_id: str
    evidence_type: str
    source: str
    severity: EvidenceSeverity
    confidence: float
    description: str
    explanation: Optional[str] = None
    entities: List[str] = []
    freshness: FreshnessState
    weight: float  # Computed weight in fusion
    contribution: float  # Actual contribution to score (+/-)


class FusionResult(BaseModel):
    """Complete fusion result with explanation"""
    case_id: str
    recommendation: RecommendationType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

    # Evidence breakdown
    primary_reasons: List[str] = []
    supporting_evidence: List[EvidenceContribution] = []
    contradicting_evidence: List[EvidenceContribution] = []

    # Data freshness
    data_freshness_warnings: List[str] = []
    stale_evidence_count: int = 0
    unavailable_evidence_count: int = 0
    adverse_evidence_count: int = 0

    # Limitations
    limitations: List[str] = []

    # Recommended action
    recommended_action: str

    # Metadata
    evidence_atoms_considered: int = 0
    fusion_version: str = "1.0"
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Score breakdown (for transparency)
    positive_score: float = 0.0
    negative_score: float = 0.0
    net_score: float = 0.0
    critical_flags: List[str] = []
    freshness_breakdown: Dict[str, int] = {}