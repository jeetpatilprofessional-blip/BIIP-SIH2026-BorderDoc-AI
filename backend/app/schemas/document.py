# BIIP-SIH2026 Document Schemas
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


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


class DocumentFieldRead(BaseModel):
    id: str
    field_name: str
    field_category: str
    value: Optional[str] = None
    normalized_value: Optional[str] = None
    confidence: float
    source: str
    bbox: Optional[List[int]] = None  # [x, y, w, h]
    is_valid: Optional[bool] = None
    validation_error: Optional[str] = None
    matched_field_id: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentRead(BaseModel):
    id: str
    case_id: str
    person_id: Optional[str] = None
    document_type: DocumentType
    document_subtype: Optional[str] = None
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    quality_score: Optional[float] = None
    quality_issues: Optional[List[str]] = None
    status: DocumentStatus
    processing_error: Optional[str] = None
    mrz_raw: Optional[str] = None
    mrz_valid: Optional[bool] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    fields: List[DocumentFieldRead] = []

    class Config:
        from_attributes = True


class DocumentUpload(BaseModel):
    document_type: DocumentType
    document_subtype: Optional[str] = None


class DocumentProcessRequest(BaseModel):
    document_id: str
    run_ocr: bool = True
    run_mrz: bool = True
    run_barcode: bool = True
    run_validation: bool = True
    run_tamper: bool = True