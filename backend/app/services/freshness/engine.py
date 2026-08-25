# BIIP-SIH2026 Freshness Engine
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select

from app.services.freshness.models import (
    FreshnessState,
    FreshnessPolicy,
    FreshnessCheckResult,
    DEFAULT_POLICIES,
)
from app.models.status_cache import StatusCache, FreshnessState as CacheFreshnessState, StatusType
from app.core.config import get_settings


class FreshnessEngine:
    """Evaluate freshness of cached authoritative data"""

    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()
        self.policies = {f"{p.source}:{p.status_type}": p for p in DEFAULT_POLICIES}

    def check_freshness(self, case_id: str) -> List[FreshnessCheckResult]:
        """Check freshness of all cached status records for a case"""
        results = []

        status_records = self.session.exec(
            select(StatusCache).where(StatusCache.case_id == case_id)
        ).all()

        for record in status_records:
            result = self._evaluate_record(record)
            results.append(result)

        return results

    def check_freshness_by_id(self, record_id: str) -> Optional[FreshnessCheckResult]:
        """Check freshness of a specific status record by ID"""
        record = self.session.get(StatusCache, record_id)
        if record:
            return self._evaluate_record(record)
        return None

    def _evaluate_record(self, record: StatusCache) -> FreshnessCheckResult:
        """Evaluate a single status record"""
        now = datetime.utcnow()

        # Handle None last_synced_at
        if record.last_synced_at is None:
            hours_since_sync = None
        else:
            hours_since_sync = (now - record.last_synced_at).total_seconds() / 3600

        # Get policy
        policy_key = f"{record.source}:{record.status_type.value}"
        policy = self.policies.get(policy_key)

        if policy:
            policy_hours = policy.max_age_hours
        else:
            # Default from settings
            if record.status_type == StatusType.WATCHLIST:
                policy_hours = self.settings.FRESHNESS_WATCHLIST_HOURS
            elif record.status_type == StatusType.VISA:
                policy_hours = self.settings.FRESHNESS_VISA_HOURS
            elif record.status_type == StatusType.PASSPORT:
                policy_hours = self.settings.FRESHNESS_PASSPORT_HOURS
            else:
                policy_hours = 24

        # Determine freshness state
        # Check for adverse status first (is_adverse flag or adverse status)
        if record.freshness == CacheFreshnessState.CONFIRMED_ADVERSE or record.is_adverse:
            state = FreshnessState.CONFIRMED_ADVERSE
        elif record.freshness == CacheFreshnessState.UNAVAILABLE:
            state = FreshnessState.UNAVAILABLE
        elif hours_since_sync is None:
            state = FreshnessState.UNAVAILABLE
        elif hours_since_sync <= policy_hours:
            state = FreshnessState.VERIFIED_FRESH
        else:
            state = FreshnessState.VERIFIED_STALE

        # Build explanation
        if state == FreshnessState.VERIFIED_FRESH:
            explanation = f"Verified {hours_since_sync:.1f}h ago (policy: {policy_hours}h)"
            display_status = f"Fresh ({hours_since_sync:.0f}h)"
            display_color = "green"
        elif state == FreshnessState.VERIFIED_STALE:
            explanation = f"Stale: last sync {hours_since_sync:.1f}h ago, policy allows {policy_hours}h"
            display_status = f"Stale ({hours_since_sync:.0f}h > {policy_hours}h)"
            display_color = "orange"
        elif state == FreshnessState.UNAVAILABLE:
            explanation = "No cached data available and central service unreachable"
            display_status = "Unavailable"
            display_color = "red"
        elif state == FreshnessState.CONFIRMED_ADVERSE:
            explanation = f"Confirmed adverse: {record.adverse_reason or record.status}"
            display_status = "ADVERSE"
            display_color = "red"

        return FreshnessCheckResult(
            source=record.source,
            status_type=record.status_type.value,
            entity_identifier=record.entity_identifier,
            state=state,
            last_synced_at=record.last_synced_at,
            hours_since_sync=hours_since_sync,
            policy_hours=policy_hours,
            is_stale=(state == FreshnessState.VERIFIED_STALE),
            is_unavailable=(state == FreshnessState.UNAVAILABLE),
            is_adverse=(state == FreshnessState.CONFIRMED_ADVERSE),
            details={
                "status": record.status,
                "source_version": record.source_version,
            },
            explanation=explanation,
            display_status=display_status,
            display_color=display_color,
        )

    def update_cache_freshness(self, case_id: str):
        """Update freshness state of all cached records for a case"""
        records = self.session.exec(
            select(StatusCache).where(StatusCache.case_id == case_id)
        ).all()

        for record in records:
            result = self._evaluate_record(record)
            record.freshness = CacheFreshnessState(result.state.value)
            record.updated_at = datetime.utcnow()
            self.session.add(record)

        self.session.commit()

    def update_single_record_freshness(self, record_id: str) -> Optional[StatusCache]:
        """Update freshness of a single record by ID"""
        record = self.session.get(StatusCache, record_id)
        if not record:
            return None

        # Update last_synced_at to now (simulating a fresh sync)
        record.last_synced_at = datetime.utcnow()
        record.updated_at = datetime.utcnow()

        result = self._evaluate_record(record)
        record.freshness = CacheFreshnessState(result.state.value)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_overall_freshness(self, case_id: str) -> FreshnessState:
        """Get overall freshness state for a case - returns FreshnessState enum for test compatibility"""
        results = self.check_freshness(case_id)

        fresh = sum(1 for r in results if r.state == FreshnessState.VERIFIED_FRESH)
        stale = sum(1 for r in results if r.state == FreshnessState.VERIFIED_STALE)
        unavailable = sum(1 for r in results if r.state == FreshnessState.UNAVAILABLE)
        adverse = sum(1 for r in results if r.state == FreshnessState.CONFIRMED_ADVERSE)

        # Overall state - priority: ADVERSE > UNAVAILABLE > STALE > FRESH
        if adverse > 0:
            overall = FreshnessState.CONFIRMED_ADVERSE
        elif unavailable > 0:
            overall = FreshnessState.UNAVAILABLE
        elif stale > 0:
            overall = FreshnessState.VERIFIED_STALE
        else:
            overall = FreshnessState.VERIFIED_FRESH

        return overall

    def simulate_status_check(
        self,
        case_id: str,
        status_type: StatusType,
        entity_identifier: str,
        source: str = "SIMULATED",
        status: str = "CLEAN",
        adverse_reason: Optional[str] = None,
        hours_ago: float = 0,
    ) -> StatusCache:
        """Simulate a status check result (for demo/testing)"""
        now = datetime.utcnow()
        last_synced = now - timedelta(hours=hours_ago)

        # Determine freshness
        policy_hours = self._get_policy_hours(status_type, source)

        if status in ["REVOKED", "WATCHLISTED", "LOST", "STOLEN", "BLACKLISTED"]:
            freshness = CacheFreshnessState.CONFIRMED_ADVERSE
        elif hours_ago > policy_hours:
            freshness = CacheFreshnessState.VERIFIED_STALE
        elif hours_ago == float('inf'):  # Unavailable
            freshness = CacheFreshnessState.UNAVAILABLE
        else:
            freshness = CacheFreshnessState.VERIFIED_FRESH

        record = StatusCache(
            case_id=case_id,
            status_type=status_type,
            entity_identifier=entity_identifier,
            entity_subtype=None,
            status=status,
            freshness=freshness,
            last_synced_at=last_synced,
            freshness_policy_hours=policy_hours,
            source=source,
            is_adverse=(status in ["REVOKED", "WATCHLISTED", "LOST", "STOLEN", "BLACKLISTED"]),
            adverse_reason=adverse_reason,
        )

        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        return record

    def _get_policy_hours(self, status_type: StatusType, source: str) -> int:
        """Get policy hours for status type"""
        policy_key = f"{source}:{status_type.value}"
        policy = self.policies.get(policy_key)

        if policy:
            return policy.max_age_hours

        if status_type == StatusType.WATCHLIST:
            return self.settings.FRESHNESS_WATCHLIST_HOURS
        elif status_type == StatusType.VISA:
            return self.settings.FRESHNESS_VISA_HOURS
        elif status_type == StatusType.PASSPORT:
            return self.settings.FRESHNESS_PASSPORT_HOURS
        elif status_type == StatusType.NATIONAL_ID:
            return self.settings.FRESHNESS_NATIONAL_ID_HOURS
        else:
            return 24

    def _get_freshness_policy_hours(self, status_type: StatusType) -> int:
        """Get default freshness policy hours for a status type (test compatibility)"""
        return self._get_policy_hours(status_type, "DEFAULT")


def check_freshness(case_id: str, session: Session) -> List[FreshnessCheckResult]:
    """Convenience function"""
    engine = FreshnessEngine(session)
    return engine.check_freshness(case_id)