# BIIP-SIH2026 OCR Models
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class OCRSource(str, Enum):
    PADDLEOCR = "PADDLEOCR"
    TESSERACT = "TESSERACT"
    MRZ = "MRZ"
    BARCODE = "BARCODE"
    NFC = "NFC"


class OCRField(BaseModel):
    """Single extracted field with metadata"""
    field_name: str
    value: str
    normalized_value: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    source: OCRSource
    bbox: Optional[List[int]] = None  # [x, y, w, h]
    language: Optional[str] = None


class OCRResult(BaseModel):
    """Complete OCR result for a document"""
    document_id: str
    fields: List[OCRField]
    raw_text: Optional[str] = None
    processing_time_ms: float
    model_version: str
    warnings: List[str] = []


class MRZResult(BaseModel):
    """Parsed MRZ result"""
    document_id: str
    mrz_raw: str
    mrz_type: str  # TD1, TD2, TD3 (passport), etc.
    fields: Dict[str, str]
    check_digits_valid: bool
    check_digit_details: Dict[str, bool]
    parsing_errors: List[str] = []


class BarcodeResult(BaseModel):
    """Decoded barcode/QR result"""
    document_id: str
    barcode_type: str  # QR, PDF417, CODE128, etc.
    data: str
    parsed_fields: Dict[str, str]
    confidence: float