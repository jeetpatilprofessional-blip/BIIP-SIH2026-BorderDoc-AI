# BIIP-SIH2026 Sync Models
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class SyncStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class SyncOperationType(str, Enum):
    STATUS_CHECK = "STATUS_CHECK"           # Check watchlist/revocation/visa status
    CASE_SYNC = "CASE_SYNC"                 # Full case sync to central
    EVIDENCE_SYNC = "EVIDENCE_SYNC"         # Sync evidence atoms
    FACE_EMBEDDING_SYNC = "FACE_EMBEDDING_SYNC"  # Sync face embeddings for central matching
    RULE_UPDATE = "RULE_UPDATE"             # Pull updated rule sets
    MODEL_UPDATE = "MODEL_UPDATE"           # Pull updated models


class SyncPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SyncQueueItem(BaseModel):
    """Item in the sync queue"""
    id: str
    case_id: Optional[str] = None
    operation_type: SyncOperationType
    payload: Dict[str, Any] = {}
    priority: SyncPriority = SyncPriority.NORMAL
    status: SyncStatus = SyncStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    idempotency_key: Optional[str] = None


class SyncResult(BaseModel):
    """Result of a sync operation"""
    success: bool
    operation_id: str
    message: str
    details: Dict[str, Any] = {}
    items_processed: int = 0
    items_failed: int = 0
    server_timestamp: Optional[datetime] = None


class CentralStatusResponse(BaseModel):
    """Response from central status check API"""
    entity_identifier: str
    status_type: str
    status: str  # CLEAN, REVOKED, WATCHLISTED, LOST, STOLEN, EXPIRED, INVALID
    source: str
    source_version: str
    adverse_reason: Optional[str] = None
    last_updated: datetime
    freshness_hours: float


class CentralSyncRequest(BaseModel):
    """Request payload for central sync"""
    case_id: str
    case_data: Dict[str, Any]
    evidence_atoms: List[Dict[str, Any]] = []
    face_embeddings: List[Dict[str, Any]] = []
    officer_id: str
    terminal_id: str


class CentralSyncResponse(BaseModel):
    """Response from central sync API"""
    sync_id: str
    status: str  # ACCEPTED, PARTIAL, REJECTED
    server_timestamp: datetime
    conflicts: List[Dict[str, Any]] = []
    updated_rules_version: Optional[str] = None
    updated_models: List[str] = []


class ConnectivityStatus(BaseModel):
    """Current connectivity status"""
    is_online: bool
    last_successful_sync: Optional[datetime] = None
    pending_queue_size: int = 0
    failed_queue_size: int = 0
    estimated_backlog_hours: float = 0.0
    central_endpoint: str = ""
    last_check: datetime = Field(default_factory=datetime.utcnow)


# Simulated central responses for demo
SIMULATED_WATCHLIST = {
    "P<IND1234567": {"status": "WATCHLISTED", "reason": "Suspected document fraud ring", "source": "INTERPOL_SLTD"},
    "V<IND987654321": {"status": "CLEAN", "source": "NATIONAL_DB"},
    "N<IND11223344": {"status": "REVOKED", "reason": "Reported lost", "source": "NATIONAL_ID_REGISTRY"},
}

SIMULATED_VISA_STATUS = {
    "VISA_IND_2024_001": {"status": "VALID", "source": "VISA_SYSTEM"},
    "VISA_IND_2024_002": {"status": "EXPIRED", "source": "VISA_SYSTEM"},
    "VISA_IND_2024_003": {"status": "REVOKED", "reason": "Overstay violation", "source": "VISA_SYSTEM"},
}

SIMULATED_PASSPORT_STATUS = {
    "P<IND1234567": {"status": "VALID", "source": "PASSPORT_REGISTRY"},
    "P<IND9999999": {"status": "REVOKED", "reason": "Reported stolen", "source": "PASSPORT_REGISTRY"},
}