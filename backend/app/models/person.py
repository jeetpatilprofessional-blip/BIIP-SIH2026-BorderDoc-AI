# BIIP-SIH2026 Person Model
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import uuid


class Person(SQLModel, table=True):
    __tablename__ = "persons"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)

    # Core identity fields (from documents)
    primary_name: Optional[str] = Field(default=None)
    primary_dob: Optional[str] = Field(default=None)  # ISO format YYYY-MM-DD
    primary_nationality: Optional[str] = Field(default=None)
    primary_gender: Optional[str] = Field(default=None)

    # Face embedding for cross-document matching
    face_embedding: Optional[bytes] = Field(default=None)  # Serialized numpy array
    face_embedding_model: Optional[str] = Field(default=None)

    # Quality indicators
    identity_confidence: Optional[float] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="person")
    documents: List["Document"] = Relationship(back_populates="person")