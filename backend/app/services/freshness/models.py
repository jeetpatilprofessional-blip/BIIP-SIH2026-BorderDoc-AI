# BIIP-SIH2026 Freshness Models
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class FreshnessState(str, Enum):
    VERIFIED_FRESH = "VERIFIED_FRESH"
    VERIFIED_STALE = "VERIFIED_STALE"
    UNAVAILABLE = "UNAVAILABLE"
    CONFIRMED_ADVERSE = "CONFIRMED_ADVERSE"


class FreshnessPolicy(BaseModel):
    """Freshness policy for a data source"""
    source: str
    status_type: str
    max_age_hours: int
    warning_threshold_hours: Optional[int] = None
    critical_threshold_hours: Optional[int] = None


class FreshnessCheckResult(BaseModel):
    """Result of a freshness check"""
    source: str
    status_type: str
    entity_identifier: str
    state: FreshnessState
    last_synced_at: Optional[datetime] = None
    hours_since_sync: Optional[float] = None
    policy_hours: int
    is_stale: bool = False
    is_unavailable: bool = False
    is_adverse: bool = False
    details: Dict[str, Any] = {}

    # Human-readable explanation
    explanation: str = ""

    # For UI display
    display_status: str = ""  # "Fresh", "Stale (6h)", "Unavailable", "ADVERSE"
    display_color: str = ""   # "green", "yellow", "red", "orange"

    # Test compatibility properties
    @property
    def freshness(self) -> FreshnessState:
        """Alias for state for test compatibility"""
        return self.state

    @property
    def age_hours(self) -> Optional[float]:
        """Alias for hours_since_sync for test compatibility"""
        return self.hours_since_sync


# Default freshness policies
DEFAULT_POLICIES = [
    FreshnessPolicy(source="INTERPOL_SLTD", status_type="WATCHLIST", max_age_hours=6, warning_threshold_hours=3, critical_threshold_hours=12),
    FreshnessPolicy(source="NATIONAL_DB", status_type="WATCHLIST", max_age_hours=6, warning_threshold_hours=3, critical_threshold_hours=12),
    FreshnessPolicy(source="VISA_SYSTEM", status_type="VISA", max_age_hours=24, warning_threshold_hours=12, critical_threshold_hours=48),
    FreshnessPolicy(source="PASSPORT_REGISTRY", status_type="PASSPORT", max_age_hours=168, warning_threshold_hours=72, critical_threshold_hours=336),
    FreshnessPolicy(source="NATIONAL_ID_REGISTRY", status_type="NATIONAL_ID", max_age_hours=168, warning_threshold_hours=72, critical_threshold_hours=336),
]