# BIIP-SIH2026 Sync Queue Model
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid


class SyncStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CONFLICT = "CONFLICT"


class SyncOperation(str, Enum):
    CASE_CREATE = "CASE_CREATE"
    CASE_UPDATE = "CASE_UPDATE"
    EVIDENCE_SYNC = "EVIDENCE_SYNC"
    STATUS_REFRESH = "STATUS_REFRESH"
    OFFICER_ACTION = "OFFICER_ACTION"
    AUDIT_SYNC = "AUDIT_SYNC"


class SyncQueue(SQLModel, table=True):
    __tablename__ = "sync_queue"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    operation: SyncOperation = Field(index=True)
    entity_type: str = Field(index=True)  # "case", "evidence", "status", etc.
    entity_id: str = Field(index=True)

    # Payload
    payload: str = Field()  # JSON

    # State
    status: SyncStatus = Field(default=SyncStatus.PENDING, index=True)
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=3)

    # Error tracking
    last_error: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    # For conflict resolution
    local_version: Optional[str] = Field(default=None)
    remote_version: Optional[str] = Field(default=None)