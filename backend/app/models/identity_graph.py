# BIIP-SIH2026 Identity Graph Models
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import uuid


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


class IdentityNode(SQLModel, table=True):
    __tablename__ = "identity_nodes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)

    node_type: NodeType = Field(index=True)
    entity_id: str = Field(index=True)  # Reference to actual entity (document_id, person_id, etc.)
    label: str  # Display label

    # Properties (JSON)
    properties: Optional[str] = Field(default=None)

    # Confidence score
    confidence: float = Field(default=1.0)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="identity_nodes")
    outgoing_edges: List["IdentityEdge"] = Relationship(
        back_populates="source_node",
        sa_relationship_kwargs={"foreign_keys": "IdentityEdge.source_node_id"}
    )
    incoming_edges: List["IdentityEdge"] = Relationship(
        back_populates="target_node",
        sa_relationship_kwargs={"foreign_keys": "IdentityEdge.target_node_id"}
    )


class IdentityEdge(SQLModel, table=True):
    __tablename__ = "identity_edges"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)

    source_node_id: str = Field(foreign_key="identity_nodes.id", index=True)
    target_node_id: str = Field(foreign_key="identity_nodes.id", index=True)

    edge_type: EdgeType = Field(index=True)
    weight: float = Field(default=1.0)  # Confidence/strength
    properties: Optional[str] = Field(default=None)  # JSON

    # Evidence atoms supporting this edge
    evidence_atom_ids: Optional[str] = Field(default=None)  # JSON array

    # Confidence score (alias for weight for test compatibility)
    confidence: float = Field(default=1.0)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    case: Optional["Case"] = Relationship()
    source_node: Optional[IdentityNode] = Relationship(
        back_populates="outgoing_edges",
        sa_relationship_kwargs={"foreign_keys": "IdentityEdge.source_node_id"}
    )
    target_node: Optional[IdentityNode] = Relationship(
        back_populates="incoming_edges",
        sa_relationship_kwargs={"foreign_keys": "IdentityEdge.target_node_id"}
    )