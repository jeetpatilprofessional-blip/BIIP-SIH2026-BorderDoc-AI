# BIIP-SIH2026 Tamper Result Model
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid


class TamperResult(SQLModel, table=True):
    __tablename__ = "tamper_results"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)
    document_id: str = Field(foreign_key="documents.id", index=True)

    # Overall result
    tampered: bool = Field(default=False)
    confidence: float = Field(default=0.0)

    # Layer results (JSON)
    cross_field_consistency: Optional[str] = Field(default=None)  # JSON
    image_analysis: Optional[str] = Field(default=None)  # JSON
    photo_consistency: Optional[str] = Field(default=None)  # JSON

    # Suspicious regions for heatmap
    suspicious_regions: Optional[str] = Field(default=None)  # JSON array of regions

    # Reasons
    reasons: Optional[str] = Field(default=None)  # JSON array of reason strings

    # Details
    details_json: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="tamper_results")
    document: Optional["Document"] = Relationship()