# BIIP-SIH2026 Document Model
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import uuid


class DocumentType(str, Enum):
    PASSPORT = "PASSPORT"
    VISA = "VISA"
    NATIONAL_ID = "NATIONAL_ID"
    DRIVING_LICENCE = "DRIVING_LICENCE"
    PERMIT = "PERMIT"
    TRAVEL_AUTHORIZATION = "TRAVEL_AUTHORIZATION"


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    REJECTED_QUALITY = "REJECTED_QUALITY"


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)
    person_id: Optional[str] = Field(default=None, foreign_key="persons.id", index=True)

    document_type: DocumentType = Field(index=True)
    document_subtype: Optional[str] = Field(default=None)  # e.g., "TOURIST", "WORK", "STUDENT" for visa
    document_number: Optional[str] = Field(default=None, index=True)  # Document number from MRZ/barcode

    # File info
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    image_width: Optional[int] = Field(default=None)
    image_height: Optional[int] = Field(default=None)

    # Capture quality
    quality_score: Optional[float] = Field(default=None)
    quality_issues: Optional[str] = Field(default=None)  # JSON array of issues

    # Status
    status: DocumentStatus = Field(default=DocumentStatus.UPLOADED, index=True)
    processing_error: Optional[str] = Field(default=None)

    # MRZ
    mrz_raw: Optional[str] = Field(default=None)
    mrz_valid: Optional[bool] = Field(default=None)

    # Timestamps
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None)

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="documents")
    person: Optional["Person"] = Relationship(back_populates="documents")
    fields: List["DocumentField"] = Relationship(back_populates="document")