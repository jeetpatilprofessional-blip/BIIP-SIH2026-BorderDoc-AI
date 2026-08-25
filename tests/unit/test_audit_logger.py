"""
Unit tests for AuditLogger
Tests immutable audit trail with hash chain verification
"""
import pytest
import hashlib
from datetime import datetime
from unittest.mock import Mock
from sqlmodel import Session

from app.services.audit.logger import AuditLogger
from app.models.audit import AuditLog


@pytest.fixture
def mock_session():
    session = Mock(spec=Session)
    return session


@pytest.fixture
def audit_logger(mock_session):
    return AuditLogger(mock_session)


class TestAuditLogger:
    """Test audit logging functionality"""

    def test_log_action_creates_record(self, audit_logger, mock_session):
        """Test that log_action creates an audit record"""
        audit_logger.log_action(
            case_id="case-1",
            action="CASE_CREATED",
            actor_id="officer-1",
            actor_type="OFFICER",
            result="SUCCESS",
            details={"case_number": "TEST-001"},
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_log_action_includes_timestamp(self, audit_logger, mock_session):
        """Test that audit record includes timestamp"""
        before = datetime.utcnow()
        audit_logger.log_action(
            case_id="case-1",
            action="CASE_CREATED",
            actor_id="officer-1",
            actor_type="OFFICER",
            result="SUCCESS",
        )
        after = datetime.utcnow()

        record = mock_session.add.call_args[0][0]
        assert before <= record.timestamp <= after

    def test_log_action_includes_hash(self, audit_logger, mock_session):
        """Test that audit record includes hash"""
        audit_logger.log_action(
            case_id="case-1",
            action="CASE_CREATED",
            actor_id="officer-1",
            actor_type="OFFICER",
            result="SUCCESS",
        )

        record = mock_session.add.call_args[0][0]
        assert record.hash is not None
        assert len(record.hash) > 0

    def test_log_action_hash_chain(self, audit_logger, mock_session):
        """Test that each record's hash includes previous hash"""
        # First record
        audit_logger.log_action(
            case_id="case-1",
            action="CASE_CREATED",
            actor_id="officer-1",
            actor_type="OFFICER",
            result="SUCCESS",
        )
        first_record = mock_session.add.call_args_list[0][0][0]

        # Second record - should reference first record's hash
        audit_logger.log_action(
            case_id="case-1",
            action="DOCUMENT_UPLOADED",
            actor_id="officer-1",
            actor_type="OFFICER",
            result="SUCCESS",
            previous_hash=first_record.hash,
        )
        second_record = mock_session.add.call_args_list[1][0][0]

        assert second_record.previous_hash == first_record.hash

    def test_log_action_without_details(self, audit_logger, mock_session):
        """Test audit logging without details"""
        audit_logger.log_action(
            case_id="case-1",
            action="CASE_UPDATED",
            actor_id="officer-1",
            actor_type="OFFICER",
            result="SUCCESS",
        )

        record = mock_session.add.call_args[0][0]
        assert record.details is None

    def test_log_action_failure(self, audit_logger, mock_session):
        """Test audit logging for failures"""
        audit_logger.log_action(
            case_id="case-1",
            action="DOCUMENT_PROCESSED",
            actor_id="SYSTEM",
            actor_type="SYSTEM",
            result="FAILURE",
            details={"error": "OCR failed"},
        )

        record = mock_session.add.call_args[0][0]
        assert record.result == "FAILURE"

    def test_log_document_uploaded(self, audit_logger, mock_session):
        """Test specific document upload logging"""
        audit_logger.log_document_uploaded(
            case_id="case-1",
            document_id="doc-1",
            document_type="PASSPORT",
            actor_id="officer-1",
        )

        mock_session.add.assert_called_once()
        record = mock_session.add.call_args[0][0]
        assert record.action == "DOCUMENT_UPLOADED"
        assert record.entity_type == "DOCUMENT"
        assert record.entity_id == "doc-1"

    def test_log_face_verified(self, audit_logger, mock_session):
        """Test face verification logging"""
        audit_logger.log_face_verified(
            case_id="case-1",
            document_id="doc-1",
            match_result="MATCH",
            match_score=0.92,
            liveness_result="LIVE",
            actor_id="SYSTEM",
        )

        record = mock_session.add.call_args[0][0]
        assert record.action == "FACE_VERIFIED"
        assert record.details["match_result"] == "MATCH"
        assert record.details["match_score"] == 0.92

    def test_log_officer_decision(self, audit_logger, mock_session):
        """Test officer decision logging"""
        audit_logger.log_officer_decision(
            case_id="case-1",
            decision="ALLOW",
            reason="Documents verified",
            officer_id="officer-1",
        )

        record = mock_session.add.call_args[0][0]
        assert record.action == "OFFICER_DECISION"
        assert record.details["decision"] == "ALLOW"

    def test_log_evidence_generated(self, audit_logger, mock_session):
        """Test evidence generation logging"""
        audit_logger.log_evidence_generated(
            case_id="case-1",
            evidence_count=15,
            atom_types=["DOCUMENT_VALID", "FACE_MATCH", "WATCHLIST_CLEAN"],
            actor_id="SYSTEM",
        )

        record = mock_session.add.call_args[0][0]
        assert record.action == "EVIDENCE_GENERATED"
        assert record.details["evidence_count"] == 15

    def test_log_fusion_completed(self, audit_logger, mock_session):
        """Test fusion completion logging"""
        audit_logger.log_fusion_completed(
            case_id="case-1",
            recommendation="LOW_CONCERN",
            positive_score=0.85,
            negative_score=0.05,
            net_score=0.80,
            confidence=0.90,
            actor_id="SYSTEM",
        )

        record = mock_session.add.call_args[0][0]
        assert record.action == "FUSION_COMPLETED"
        assert record.details["recommendation"] == "LOW_CONCERN"


class TestHashChainVerification:
    """Test audit trail integrity verification"""

    def test_verify_chain_intact(self, audit_logger, mock_session):
        """Test verification of intact hash chain"""
        records = [
            AuditLog(id="1", hash="abc123", previous_hash=None),
            AuditLog(id="2", hash="def456", previous_hash="abc123"),
            AuditLog(id="3", hash="ghi789", previous_hash="def456"),
        ]
        mock_session.exec.return_value.all.return_value = records

        result = audit_logger.verify_chain("case-1")

        assert result.intact is True
        assert result.broken_links == 0

    def test_verify_chain_broken(self, audit_logger, mock_session):
        """Test verification of broken hash chain"""
        records = [
            AuditLog(id="1", hash="abc123", previous_hash=None),
            AuditLog(id="2", hash="def456", previous_hash="abc123"),
            AuditLog(id="3", hash="ghi789", previous_hash="WRONG_HASH"),  # BROKEN!
        ]
        mock_session.exec.return_value.all.return_value = records

        result = audit_logger.verify_chain("case-1")

        assert result.intact is False
        assert result.broken_links >= 1

    def test_verify_chain_empty(self, audit_logger, mock_session):
        """Test verification of empty audit trail"""
        mock_session.exec.return_value.all.return_value = []

        result = audit_logger.verify_chain("case-1")

        assert result.intact is True
        assert result.broken_links == 0


class TestSpecificAuditActions:
    """Test specific audit action types"""

    def test_log_status_check(self, audit_logger, mock_session):
        """Test status check logging"""
        audit_logger.log_status_check(
            case_id="case-1",
            status_type="WATCHLIST",
            entity_identifier="P<IND12345678",
            result="CLEAN",
            freshness="VERIFIED_FRESH",
            actor_id="SYSTEM",
        )

        record = mock_session.add.call_args[0][0]
        assert record.action == "STATUS_CHECK_COMPLETED"
        assert record.details["status_type"] == "WATCHLIST"
        assert record.details["freshness"] == "VERIFIED_FRESH"

    def test_log_sync_triggered(self, audit_logger, mock_session):
        """Test sync trigger logging"""
        audit_logger.log_sync_triggered(
            case_id="case-1",
            operation_type="STATUS_CHECK",
            priority="HIGH",
            actor_id="SYSTEM",
        )

        record = mock_session.add.call_args[0][0]
        assert record.action == "SYNC_TRIGGERED"
        assert record.details["operation_type"] == "STATUS_CHECK"

    def test_log_rule_set_updated(self, audit_logger, mock_session):
        """Test rule set update logging"""
        audit_logger.log_rule_set_updated(
            rule_set_id="rules-1",
            changes=["Added EXPIRY rule for PASSPORT"],
            actor_id="admin-1",
        )

        record = mock_session.add.call_args[0][0]
        assert record.action == "RULE_SET_UPDATED"
        assert record.entity_id == "rules-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])