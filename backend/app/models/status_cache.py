# BIIP-SIH2026 Status Cache Model
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid


class StatusType(str, Enum):
    PASSPORT = "PASSPORT"
    VISA = "VISA"
    WATCHLIST = "WATCHLIST"
    REVOCATION = "REVOCATION"
    LOST_STOLEN = "LOST_STOLEN"
    TRAVEL_HISTORY = "TRAVEL_HISTORY"
    NATIONAL_ID = "NATIONAL_ID"


class FreshnessState(str, Enum):
    VERIFIED_FRESH = "VERIFIED_FRESH"
    VERIFIED_STALE = "VERIFIED_STALE"
    UNAVAILABLE = "UNAVAILABLE"
    CONFIRMED_ADVERSE = "CONFIRMED_ADVERSE"


class StatusCache(SQLModel, table=True):
    __tablename__ = "status_cache"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # What this status is for
    case_id: Optional[str] = Field(default=None, index=True)  # Optional case association
    status_type: StatusType = Field(index=True)
    entity_identifier: str = Field(index=True)  # passport number, visa number, etc.
    entity_subtype: Optional[str] = Field(default=None)  # e.g., visa type

    # Status value
    status: str = Field(index=True)  # "VALID", "EXPIRED", "REVOKED", "WATCHLISTED", "CLEAN", etc.
    details: Optional[str] = Field(default=None)  # JSON

    # Freshness
    freshness: FreshnessState = Field(default=FreshnessState.VERIFIED_FRESH, index=True)
    last_synced_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    freshness_policy_hours: int = Field(default=24)

    # Source
    source: str = Field(default="SIMULATED")  # "INTERPOL", "NATIONAL_DB", "SIMULATED"
    source_version: Optional[str] = Field(default=None)

    # For adverse results
    is_adverse: bool = Field(default=False)
    adverse_reason: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)