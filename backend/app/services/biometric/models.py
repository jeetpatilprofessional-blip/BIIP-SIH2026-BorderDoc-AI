# BIIP-SIH2026 Biometric Models
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class FaceMatchResult(str, Enum):
    MATCH = "MATCH"
    INCONCLUSIVE = "INCONCLUSIVE"
    MISMATCH = "MISMATCH"


class LivenessResult(str, Enum):
    LIVE = "LIVE"
    INCONCLUSIVE = "INCONCLUSIVE"
    SPOOF_SUSPECTED = "SPOOF_SUSPECTED"
    NOT_CHECKED = "NOT_CHECKED"


class FaceQualityIssue(str, Enum):
    BLUR = "BLUR"
    GLARE = "GLARE"
    POSE = "POSE"
    ILLUMINATION = "ILLUMINATION"
    OCCLUSION = "OCCLUSION"
    LOW_RESOLUTION = "LOW_RESOLUTION"


class FaceQualityResult(BaseModel):
    """Face quality assessment"""
    overall_score: float = Field(ge=0.0, le=1.0)
    issues: List[FaceQualityIssue] = []
    details: Dict[str, float] = {}  # e.g., {"blur": 0.2, "pose": 0.8}
    is_sufficient: bool = True
    recommendation: Optional[str] = None


class FaceVerificationResult(BaseModel):
    """Face verification result"""
    match_result: FaceMatchResult
    similarity_score: float = Field(ge=0.0, le=1.0)
    threshold_used: float
    live_face_quality: FaceQualityResult
    document_face_quality: Optional[FaceQualityResult] = None
    processing_time_ms: float
    model_version: str
    limitations: List[str] = [
        "PROTOTYPE: Not certified for production use",
        "Threshold tuning required for operational deployment",
        "Performance varies with capture conditions",
    ]


class LivenessResultDetail(BaseModel):
    """Detailed liveness check result"""
    result: LivenessResult
    confidence: float = Field(ge=0.0, le=1.0)
    method: str  # "passive_texture", "active_challenge", "combined"
    details: Dict[str, Any] = {}
    challenge_passed: Optional[bool] = None
    processing_time_ms: float
    limitations: List[str] = [
        "PROTOTYPE LIVENESS: Not iBeta certified",
        "Limited presentation attack detection",
        "Not suitable for high-security environments without certified SDK",
    ]