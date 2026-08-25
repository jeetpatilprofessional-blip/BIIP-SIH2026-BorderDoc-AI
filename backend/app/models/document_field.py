# BIIP-SIH2026 Document Field Model
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid


class DocumentField(SQLModel, table=True):
    __tablename__ = "document_fields"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)

    # Field identification
    field_name: str = Field(index=True)  # e.g., "date_of_birth", "passport_number"
    field_category: str = Field(default="general")  # "mrz", "visual", "barcode", "nfc"

    # Extracted value
    value: Optional[str] = Field(default=None)
    normalized_value: Optional[str] = Field(default=None)

    # Confidence & source
    confidence: float = Field(default=0.0)
    source: str = Field(default="OCR")  # "OCR", "MRZ", "BARCODE", "NFC", "MANUAL"

    # Bounding box [x, y, w, h] relative to image
    bbox_x: Optional[int] = Field(default=None)
    bbox_y: Optional[int] = Field(default=None)
    bbox_w: Optional[int] = Field(default=None)
    bbox_h: Optional[int] = Field(default=None)

    # Validation
    is_valid: Optional[bool] = Field(default=None)
    validation_error: Optional[str] = Field(default=None)

    # Cross-reference
    matched_field_id: Optional[str] = Field(default=None)  # Links to matching field in another document

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    document: Optional["Document"] = Relationship(back_populates="fields")