"""
Unit tests for FreshnessEngine
Tests the 4-state freshness logic: VERIFIED_FRESH, VERIFIED_STALE, UNAVAILABLE, CONFIRMED_ADVERSE
Critical: UNAVAILABLE != CLEAR
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from sqlmodel import Session

from app.services.freshness.engine import FreshnessEngine
from app.models.status_cache import StatusCache, StatusType, FreshnessState as CacheFreshnessState
from app.models.case import Case


@pytest.fixture
def mock_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    # Mock exec() to return an object with .all() method
    mock_exec_result = Mock()
    mock_exec_result.all.return_value = []
    session.exec.return_value = mock_exec_result
    return session


@pytest.fixture
def freshness_engine(mock_session):
    """Create FreshnessEngine instance with mocked session"""
    return FreshnessEngine(mock_session)


class TestFreshnessEngine:
    """Test FreshnessEngine core functionality"""

    def test_check_freshness_fresh_record(self, freshness_engine, mock_session):
        """Test that recently updated record is VERIFIED_FRESH"""
        now = datetime.utcnow()
        record = StatusCache(
            id="test-1",
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            status="CLEAN",
            freshness=CacheFreshnessState.VERIFIED_FRESH,
            last_synced_at=now - timedelta(hours=2),
            freshness_policy_hours=6,
            source="NATIONAL_DB",
            is_adverse=False,
        )
        mock_session.get.return_value = record

        result = freshness_engine.check_freshness_by_id("test-1")

        assert result.freshness == CacheFreshnessState.VERIFIED_FRESH
        assert result.is_stale is False
        assert result.is_unavailable is False

    def test_check_freshness_stale_record(self, freshness_engine, mock_session):
        """Test that record past freshness window is VERIFIED_STALE"""
        now = datetime.utcnow()
        record = StatusCache(
            id="test-2",
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            status="CLEAN",
            freshness=CacheFreshnessState.VERIFIED_FRESH,
            last_synced_at=now - timedelta(hours=12),
            freshness_policy_hours=6,
            source="NATIONAL_DB",
            is_adverse=False,
        )
        mock_session.get.return_value = record

        result = freshness_engine.check_freshness_by_id("test-2")

        assert result.freshness == CacheFreshnessState.VERIFIED_STALE
        assert result.is_stale is True
        assert result.is_unavailable is False

    def test_check_freshness_unavailable_record(self, freshness_engine, mock_session):
        """Test that never-synced record is UNAVAILABLE (NOT CLEAR!)"""
        record = StatusCache(
            id="test-3",
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            status="CLEAN",
            freshness=CacheFreshnessState.UNAVAILABLE,
            last_synced_at=None,
            freshness_policy_hours=6,
            source="NATIONAL_DB",
            is_adverse=False,
        )
        mock_session.get.return_value = record

        result = freshness_engine.check_freshness_by_id("test-3")

        assert result.freshness == CacheFreshnessState.UNAVAILABLE
        assert result.is_unavailable is True
        # CRITICAL: UNAVAILABLE must never be treated as CLEAR
        assert result.is_adverse is False

    def test_check_freshness_confirmed_adverse(self, freshness_engine, mock_session):
        """Test that confirmed adverse record is CONFIRMED_ADVERSE"""
        now = datetime.utcnow()
        record = StatusCache(
            id="test-4",
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            status="WATCHLISTED",
            freshness=CacheFreshnessState.CONFIRMED_ADVERSE,
            last_synced_at=now - timedelta(hours=2),
            freshness_policy_hours=6,
            source="INTERPOL_SLTD",
            is_adverse=True,
            adverse_reason="Suspected document fraud",
        )
        mock_session.get.return_value = record

        result = freshness_engine.check_freshness_by_id("test-4")

        assert result.freshness == CacheFreshnessState.CONFIRMED_ADVERSE
        assert result.is_adverse is True

    def test_evaluate_record_fresh(self, freshness_engine):
        """Test _evaluate_record for fresh data"""
        now = datetime.utcnow()
        record = StatusCache(
            id="eval-1",
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            status="CLEAN",
            freshness=CacheFreshnessState.VERIFIED_FRESH,
            last_synced_at=now - timedelta(hours=1),
            freshness_policy_hours=6,
            source="NATIONAL_DB",
            is_adverse=False,
        )

        result = freshness_engine._evaluate_record(record)

        assert result.freshness == CacheFreshnessState.VERIFIED_FRESH
        assert abs(result.age_hours - 1.0) < 0.001  # Allow floating point precision
        assert result.is_stale is False

    def test_evaluate_record_stale(self, freshness_engine):
        """Test _evaluate_record for stale data"""
        now = datetime.utcnow()
        record = StatusCache(
            id="eval-2",
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            status="CLEAN",
            freshness=CacheFreshnessState.VERIFIED_FRESH,
            last_synced_at=now - timedelta(hours=10),
            freshness_policy_hours=6,
            source="NATIONAL_DB",
            is_adverse=False,
        )

        result = freshness_engine._evaluate_record(record)

        assert result.freshness == CacheFreshnessState.VERIFIED_STALE
        assert abs(result.age_hours - 10.0) < 0.001  # Allow floating point precision
        assert result.is_stale is True

    def test_evaluate_record_no_sync_unavailable(self, freshness_engine):
        """Test _evaluate_record for never-synced data - MUST be UNAVAILABLE"""
        record = StatusCache(
            id="eval-3",
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            status="CLEAN",
            freshness=CacheFreshnessState.VERIFIED_FRESH,
            last_synced_at=None,
            freshness_policy_hours=6,
            source="NATIONAL_DB",
            is_adverse=False,
        )

        result = freshness_engine._evaluate_record(record)

        assert result.freshness == CacheFreshnessState.UNAVAILABLE
        assert result.age_hours is None
        assert result.is_unavailable is True

    def test_evaluate_record_adverse(self, freshness_engine):
        """Test _evaluate_record for adverse record"""
        now = datetime.utcnow()
        record = StatusCache(
            id="eval-4",
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            status="WATCHLISTED",
            freshness=CacheFreshnessState.VERIFIED_FRESH,
            last_synced_at=now - timedelta(hours=1),
            freshness_policy_hours=6,
            source="INTERPOL_SLTD",
            is_adverse=True,
            adverse_reason="Fraud alert",
        )

        result = freshness_engine._evaluate_record(record)

        assert result.freshness == CacheFreshnessState.CONFIRMED_ADVERSE
        assert result.is_adverse is True

    def test_get_overall_freshness_all_fresh(self, freshness_engine, mock_session):
        """Test overall freshness when all records are fresh"""
        now = datetime.utcnow()
        records = [
            StatusCache(
                id=f"r{i}",
                case_id="case-1",
                status_type=StatusType.WATCHLIST,
                entity_identifier="TEST123",
                status="CLEAN",
                freshness=CacheFreshnessState.VERIFIED_FRESH,
                last_synced_at=now - timedelta(hours=1),
                freshness_policy_hours=6,
                source="NATIONAL_DB",
                is_adverse=False,
            )
            for i in range(3)
        ]
        mock_session.exec.return_value.all.return_value = records

        result = freshness_engine.get_overall_freshness("case-1")

        assert result == CacheFreshnessState.VERIFIED_FRESH

    def test_get_overall_freshness_any_adverse(self, freshness_engine, mock_session):
        """Test overall freshness when any record is adverse - ADVERSE WINS"""
        now = datetime.utcnow()
        records = [
            StatusCache(
                id="r1",
                case_id="case-1",
                status_type=StatusType.WATCHLIST,
                entity_identifier="TEST123",
                status="CLEAN",
                freshness=CacheFreshnessState.VERIFIED_FRESH,
                last_synced_at=now - timedelta(hours=1),
                freshness_policy_hours=6,
                source="NATIONAL_DB",
                is_adverse=False,
            ),
            StatusCache(
                id="r2",
                case_id="case-1",
                status_type=StatusType.VISA,
                entity_identifier="VISA123",
                status="WATCHLISTED",
                freshness=CacheFreshnessState.CONFIRMED_ADVERSE,
                last_synced_at=now - timedelta(hours=1),
                freshness_policy_hours=6,
                source="VISA_SYSTEM",
                is_adverse=True,
            ),
        ]
        mock_session.exec.return_value.all.return_value = records

        result = freshness_engine.get_overall_freshness("case-1")

        assert result == CacheFreshnessState.CONFIRMED_ADVERSE

    def test_get_overall_freshness_any_unavailable(self, freshness_engine, mock_session):
        """Test overall freshness when any record is unavailable"""
        now = datetime.utcnow()
        records = [
            StatusCache(
                id="r1",
                case_id="case-1",
                status_type=StatusType.WATCHLIST,
                entity_identifier="TEST123",
                status="CLEAN",
                freshness=CacheFreshnessState.VERIFIED_FRESH,
                last_synced_at=now - timedelta(hours=1),
                freshness_policy_hours=6,
                source="NATIONAL_DB",
                is_adverse=False,
            ),
            StatusCache(
                id="r2",
                case_id="case-1",
                status_type=StatusType.VISA,
                entity_identifier="VISA123",
                status="CLEAN",
                freshness=CacheFreshnessState.UNAVAILABLE,
                last_synced_at=None,
                freshness_policy_hours=6,
                source="VISA_SYSTEM",
                is_adverse=False,
            ),
        ]
        mock_session.exec.return_value.all.return_value = records

        result = freshness_engine.get_overall_freshness("case-1")

        assert result == CacheFreshnessState.UNAVAILABLE

    def test_get_overall_freshness_any_stale(self, freshness_engine, mock_session):
        """Test overall freshness when any record is stale (no adverse/unavailable)"""
        now = datetime.utcnow()
        records = [
            StatusCache(
                id="r1",
                case_id="case-1",
                status_type=StatusType.WATCHLIST,
                entity_identifier="TEST123",
                status="CLEAN",
                freshness=CacheFreshnessState.VERIFIED_FRESH,
                last_synced_at=now - timedelta(hours=1),
                freshness_policy_hours=6,
                source="NATIONAL_DB",
                is_adverse=False,
            ),
            StatusCache(
                id="r2",
                case_id="case-1",
                status_type=StatusType.WATCHLIST,
                entity_identifier="VISA123",
                status="CLEAN",
                freshness=CacheFreshnessState.VERIFIED_STALE,
                last_synced_at=now - timedelta(hours=12),
                freshness_policy_hours=6,
                source="NATIONAL_DB",
                is_adverse=False,
            ),
        ]
        mock_session.exec.return_value.all.return_value = records

        result = freshness_engine.get_overall_freshness("case-1")

        assert result == CacheFreshnessState.VERIFIED_STALE

    def test_simulate_status_check_creates_record(self, freshness_engine, mock_session):
        """Test simulate_status_check creates and returns a record"""
        result = freshness_engine.simulate_status_check(
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            source="NATIONAL_DB",
            status="CLEAN",
        )

        assert result.case_id == "case-1"
        assert result.status_type == StatusType.WATCHLIST
        assert result.entity_identifier == "TEST123"
        assert result.source == "NATIONAL_DB"
        assert result.status == "CLEAN"
        assert result.freshness == CacheFreshnessState.VERIFIED_FRESH
        assert result.is_adverse is False
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_simulate_status_check_adverse(self, freshness_engine, mock_session):
        """Test simulate_status_check with adverse result"""
        result = freshness_engine.simulate_status_check(
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="WATCHLIST123",
            source="INTERPOL_SLTD",
            status="WATCHLISTED",
            adverse_reason="Known fraudster",
        )

        assert result.status == "WATCHLISTED"
        assert result.freshness == CacheFreshnessState.CONFIRMED_ADVERSE
        assert result.is_adverse is True
        assert result.adverse_reason == "Known fraudster"

    def test_update_cache_freshness_updates_record(self, freshness_engine, mock_session):
        """Test update_cache_freshness updates last_synced_at"""
        now = datetime.utcnow()
        record = StatusCache(
            id="update-1",
            case_id="case-1",
            status_type=StatusType.WATCHLIST,
            entity_identifier="TEST123",
            status="CLEAN",
            freshness=CacheFreshnessState.VERIFIED_STALE,
            last_synced_at=now - timedelta(hours=12),
            freshness_policy_hours=6,
            source="NATIONAL_DB",
            is_adverse=False,
        )
        mock_session.get.return_value = record

        freshness_engine.update_single_record_freshness("update-1")

        assert record.last_synced_at is not None
        # The record's last_synced_at is updated to now, so it should be fresh
        assert record.freshness == CacheFreshnessState.VERIFIED_FRESH
        mock_session.add.assert_called_once_with(record)
        mock_session.commit.assert_called_once()


class TestFreshnessPolicyDefaults:
    """Test default freshness policies for different status types"""

    def test_watchlist_default_policy(self, freshness_engine):
        """Watchlist should have 6-hour freshness policy"""
        # This tests the internal _get_freshness_policy_hours method
        hours = freshness_engine._get_freshness_policy_hours(StatusType.WATCHLIST)
        assert hours == 6

    def test_visa_default_policy(self, freshness_engine):
        """Visa should have 24-hour freshness policy"""
        hours = freshness_engine._get_freshness_policy_hours(StatusType.VISA)
        assert hours == 24

    def test_passport_default_policy(self, freshness_engine):
        """Passport should have 168-hour (1 week) freshness policy"""
        hours = freshness_engine._get_freshness_policy_hours(StatusType.PASSPORT)
        assert hours == 168

    def test_national_id_default_policy(self, freshness_engine):
        """National ID should have 168-hour (1 week) freshness policy"""
        hours = freshness_engine._get_freshness_policy_hours(StatusType.NATIONAL_ID)
        assert hours == 168


if __name__ == "__main__":
    pytest.main([__file__, "-v"])