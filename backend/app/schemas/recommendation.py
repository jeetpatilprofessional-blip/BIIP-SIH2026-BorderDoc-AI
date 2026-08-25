# BIIP-SIH2026 Recommendation Schemas
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class RecommendationType(str, Enum):
    LOW_CONCERN = "LOW_CONCERN"
    SECONDARY_INSPECTION = "SECONDARY_INSPECTION"
    HIGH_CONCERN = "HIGH_CONCERN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceSummaryItem(BaseModel):
    evidence_type: str
    source: str
    severity: str
    confidence: float
    description: str
    explanation: Optional[str] = None
    entities: Optional[List[str]] = None
    freshness: str


class RecommendationRead(BaseModel):
    case_id: str
    recommendation: RecommendationType
    confidence: float
    reasoning: str
    primary_reasons: List[str]
    supporting_evidence: List[EvidenceSummaryItem]
    data_freshness_warnings: List[str]
    limitations: List[str]
    recommended_action: str
    created_at: datetime
    net_score: float = 0.0
    critical_flags: List[str] = []
    freshness_breakdown: Dict[str, int] = {}


class RecommendationDetail(BaseModel):
    case_id: str
    recommendation: RecommendationType
    confidence: float
    net_score: float = 0.0
    critical_flags: List[str] = []
    freshness_breakdown: Dict[str, int] = {}
    reasoning: str = ""
    primary_reasons: List[str] = []
    supporting_evidence: List[EvidenceSummaryItem] = []
    data_freshness_warnings: List[str] = []
    limitations: List[str] = []
    recommended_action: str = ""
    created_at: Optional[datetime] = None
    evidence_atoms: List[Dict[str, Any]] = []
    identity_graph_summary: Dict[str, Any] = {}
    freshness_summary: Dict[str, Any] = {}
    recommendation_read: Optional[RecommendationRead] = None