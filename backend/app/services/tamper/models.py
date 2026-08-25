# BIIP-SIH2026 Tamper Detection Models
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TamperLayer(str, Enum):
    CROSS_FIELD = "CROSS_FIELD"
    IMAGE_ANALYSIS = "IMAGE_ANALYSIS"
    PHOTO_CONSISTENCY = "PHOTO_CONSISTENCY"


class TamperSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SuspiciousRegion(BaseModel):
    """A suspicious region in the document image"""
    x: int
    y: int
    width: int
    height: int
    layer: TamperLayer
    severity: TamperSeverity
    description: str
    confidence: float = Field(ge=0.0, le=1.0)


class TamperLayerResult(BaseModel):
    """Result from a single tamper detection layer"""
    layer: TamperLayer
    tampered: bool
    confidence: float = Field(ge=0.0, le=1.0)
    suspicious_regions: List[SuspiciousRegion] = []
    details: Dict[str, Any] = {}
    reasons: List[str] = []


class TamperResult(BaseModel):
    """Complete tamper detection result"""
    document_id: str
    tampered: bool
    overall_confidence: float = Field(ge=0.0, le=1.0)
    layers: List[TamperLayerResult] = []
    suspicious_regions: List[SuspiciousRegion] = []
    reasons: List[str] = []
    processing_time_ms: float
    model_versions: Dict[str, str] = {}

    # Limitations disclaimer
    limitations: List[str] = [
        "PROTOTYPE: Not forensic-grade",
        "Limited to detectable artifacts",
        "Cannot detect all sophisticated forgeries",
        "Requires controlled capture conditions for best results",
    ]