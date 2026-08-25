# BIIP-SIH2026 Identity Graph Models
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class NodeType(str, Enum):
    PERSON = "PERSON"
    PASSPORT = "PASSPORT"
    VISA = "VISA"
    NATIONAL_ID = "NATIONAL_ID"
    DRIVING_LICENCE = "DRIVING_LICENCE"
    PERMIT = "PERMIT"
    TRAVEL_AUTHORIZATION = "TRAVEL_AUTHORIZATION"
    FACE = "FACE"
    TRAVEL_EVENT = "TRAVEL_EVENT"


class EdgeType(str, Enum):
    BELONGS_TO = "BELONGS_TO"
    REFERENCES = "REFERENCES"
    MATCHES = "MATCHES"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    VALIDATES = "VALIDATES"
    OCCURRED_BEFORE = "OCCURRED_BEFORE"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"


class ConflictSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GraphNode(BaseModel):
    """Node in the identity graph"""
    id: str
    node_type: NodeType
    entity_id: str  # Reference to actual entity
    label: str
    properties: Dict[str, Any] = {}
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class GraphEdge(BaseModel):
    """Edge in the identity graph"""
    id: str
    source: str  # Source node ID
    target: str  # Target node ID
    edge_type: EdgeType
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: Dict[str, Any] = {}
    evidence_ids: List[str] = []


class Conflict(BaseModel):
    """A detected conflict in the identity graph"""
    conflict_id: str
    conflict_type: str  # e.g., "DOB_MISMATCH", "FACE_MISMATCH"
    severity: ConflictSeverity
    description: str
    nodes_involved: List[str]  # Node IDs
    edges_involved: List[str]  # Edge IDs
    evidence_ids: List[str]
    suggested_action: str


class GraphSummary(BaseModel):
    """Summary of the identity graph"""
    case_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    conflicts: List[Conflict]
    face_clusters: List[Dict[str, Any]] = []
    identity_fragmentation_detected: bool = False
    multiple_identities_detected: bool = False
    statistics: Dict[str, int] = {}