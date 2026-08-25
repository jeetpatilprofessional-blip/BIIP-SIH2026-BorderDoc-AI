# BIIP-SIH2026 System Schemas
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class SystemMode(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class ComponentStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class ComponentHealth(BaseModel):
    name: str
    status: ComponentStatus
    message: Optional[str] = None
    last_check: datetime
    details: Optional[Dict[str, Any]] = None


class DatabaseFreshness(BaseModel):
    status_type: str
    source: str
    last_synced_at: datetime
    freshness_policy_hours: int
    freshness_state: str
    record_count: int


class SystemStatus(BaseModel):
    mode: SystemMode
    overall_health: ComponentStatus
    components: List[ComponentHealth]
    database_freshness: List[DatabaseFreshness]
    sync_queue_pending: int
    sync_queue_failed: int
    uptime_seconds: float
    version: str


class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str