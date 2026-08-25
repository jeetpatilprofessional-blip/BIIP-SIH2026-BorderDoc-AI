# BIIP-SIH2026 Face Result Models
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid


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


class FaceResult(SQLModel, table=True):
    __tablename__ = "face_results"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)
    document_id: Optional[str] = Field(default=None, foreign_key="documents.id", index=True)

    # Source identification
    source_type: str = Field(default="LIVE_CAPTURE")  # "LIVE_CAPTURE", "DOCUMENT_PHOTO"
    source_image_path: Optional[str] = Field(default=None)

    # Detection
    face_detected: bool = Field(default=False)
    detection_confidence: float = Field(default=0.0)
    face_bbox_x: Optional[int] = Field(default=None)
    face_bbox_y: Optional[int] = Field(default=None)
    face_bbox_w: Optional[int] = Field(default=None)
    face_bbox_h: Optional[int] = Field(default=None)

    # Quality
    quality_score: float = Field(default=0.0)
    quality_issues: Optional[str] = Field(default=None)  # JSON array of FaceQualityIssue

    # Embedding
    embedding: Optional[bytes] = Field(default=None)  # Serialized numpy array
    embedding_model: Optional[str] = Field(default=None)

    # Liveness
    liveness_result: LivenessResult = Field(default=LivenessResult.NOT_CHECKED)
    liveness_confidence: float = Field(default=0.0)
    liveness_details: Optional[str] = Field(default=None)  # JSON

    # Comparison (if this is a live face compared to document)
    compared_to_document_id: Optional[str] = Field(default=None)
    match_result: Optional[FaceMatchResult] = Field(default=None)
    match_score: Optional[float] = Field(default=None)
    match_threshold: Optional[float] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="face_results")
    document: Optional["Document"] = Relationship()