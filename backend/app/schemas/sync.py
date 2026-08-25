# BIIP-SIH2026 Sync Schemas
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


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


class SyncQueueItem(BaseModel):
    id: str
    operation: SyncOperation
    entity_type: str
    entity_id: str
    status: SyncStatus
    attempts: int
    max_attempts: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class SyncStatusResponse(BaseModel):
    pending: int
    in_progress: int
    completed: int
    failed: int
    conflict: int
    total: int
    items: List[SyncQueueItem]
    last_sync_at: Optional[datetime] = None


class SyncTrigger(BaseModel):
    force: bool = False
    operation_types: Optional[List[SyncOperation]] = None


class SyncResult(BaseModel):
    success: bool
    synced_count: int
    failed_count: int
    conflicts: List[Dict[str, Any]]
    message: str