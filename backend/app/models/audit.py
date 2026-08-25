# BIIP-SIH2026 Audit Models
from datetime import datetime
from enum import Enum
from typing import Optional, Dict
from sqlmodel import SQLModel, Field, Relationship
import uuid


class AuditEventType(str, Enum):
    CASE_CREATED = "CASE_CREATED"
    DOCUMENT_ADDED = "DOCUMENT_ADDED"
    OCR_COMPLETED = "OCR_COMPLETED"
    MRZ_VALIDATED = "MRZ_VALIDATED"
    BARCODE_CHECKED = "BARCODE_CHECKED"
    TAMPER_ANALYZED = "TAMPER_ANALYZED"
    FACE_VERIFIED = "FACE_VERIFIED"
    LIVENESS_CHECKED = "LIVENESS_CHECKED"
    GRAPH_UPDATED = "GRAPH_UPDATED"
    EVIDENCE_CREATED = "EVIDENCE_CREATED"
    STATUS_CHECKED = "STATUS_CHECKED"
    STATUS_STALE = "STATUS_STALE"
    STATUS_UNAVAILABLE = "STATUS_UNAVAILABLE"
    RECOMMENDATION_CREATED = "RECOMMENDATION_CREATED"
    OFFICER_OVERRIDE = "OFFICER_OVERRIDE"
    SYNC_STARTED = "SYNC_STARTED"
    SYNC_COMPLETED = "SYNC_COMPLETED"
    OFFLINE_MODE_ENTERED = "OFFLINE_MODE_ENTERED"
    ONLINE_MODE_RESTORED = "ONLINE_MODE_RESTORED"


# Audit Log model (immutable audit trail)
class AuditAction(str, Enum):
    CASE_CREATED = "CASE_CREATED"
    CASE_UPDATED = "CASE_UPDATED"
    CASE_CLOSED = "CASE_CLOSED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_PROCESSED = "DOCUMENT_PROCESSED"
    OCR_COMPLETED = "OCR_COMPLETED"
    MRZ_PARSED = "MRZ_PARSED"
    BARCODE_READ = "BARCODE_READ"
    FACE_CAPTURED = "FACE_CAPTURED"
    FACE_VERIFIED = "FACE_VERIFIED"
    LIVENESS_CHECKED = "LIVENESS_CHECKED"
    TAMPER_CHECKED = "TAMPER_CHECKED"
    VALIDATION_COMPLETED = "VALIDATION_COMPLETED"
    EVIDENCE_GENERATED = "EVIDENCE_GENERATED"
    FUSION_COMPLETED = "FUSION_COMPLETED"
    RECOMMENDATION_VIEWED = "RECOMMENDATION_VIEWED"
    OFFICER_DECISION = "OFFICER_DECISION"
    STATUS_CHECK_REQUESTED = "STATUS_CHECK_REQUESTED"
    STATUS_CHECK_COMPLETED = "STATUS_CHECK_COMPLETED"
    SYNC_TRIGGERED = "SYNC_TRIGGERED"
    SYNC_COMPLETED = "SYNC_COMPLETED"
    RULE_SET_UPDATED = "RULE_SET_UPDATED"
    MODEL_UPDATED = "MODEL_UPDATED"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    ACCESS_DENIED = "ACCESS_DENIED"
    EXPORT_REQUESTED = "EXPORT_REQUESTED"


class AuditResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    WARNING = "WARNING"
    PENDING = "PENDING"


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)

    event_type: AuditEventType = Field(index=True)
    module: str = Field(index=True)  # Which module generated this event

    # Event details
    details: Optional[str] = Field(default=None)  # JSON
    extra_data: Optional[str] = Field(default=None, alias="metadata")  # JSON

    # Actor
    actor_type: str = Field(default="SYSTEM")  # "SYSTEM", "OFFICER", "EXTERNAL"
    actor_id: Optional[str] = Field(default=None)

    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="audit_events")


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    action: str = Field(index=True)
    actor_id: str = Field(index=True)
    actor_type: str = Field(default="OFFICER")

    case_id: Optional[str] = Field(default=None, foreign_key="cases.id", index=True)
    entity_type: Optional[str] = Field(default=None)
    entity_id: Optional[str] = Field(default=None)
    result: str = Field(default="SUCCESS")

    details_json: Optional[str] = Field(default=None)  # JSON stored in DB

    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    correlation_id: Optional[str] = Field(default=None, index=True)

    # Immutable hash chain
    previous_hash: Optional[str] = Field(default=None)
    hash: str = Field(index=True)

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="audit_log")

    @property
    def details(self) -> Optional[Dict]:
        """Get details as dict (parsed from JSON)"""
        if self.details_json:
            import json
            return json.loads(self.details_json)
        return None

    @details.setter
    def details(self, value: Optional[Dict]):
        """Set details from dict (serializes to JSON)"""
        import json
        self.details_json = json.dumps(value) if value is not None else None