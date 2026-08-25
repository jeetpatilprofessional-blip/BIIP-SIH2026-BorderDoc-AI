# BIIP-SIH2026 Audit Logger
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import Session, select
import json

from app.models.audit import AuditLog, AuditAction, AuditResult
from app.core.config import get_settings


class AuditLogger:
    """Immutable audit trail for all system actions"""

    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()

    def log(
        self,
        action: AuditAction,
        actor_id: str,
        actor_type: str = "OFFICER",  # OFFICER, SYSTEM, API
        case_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        result: AuditResult = AuditResult.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
        previous_hash: Optional[str] = None,  # Allow explicit previous_hash for testing
    ) -> AuditLog:
        """Create an audit log entry"""

        # Create immutable record
        entry = AuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            action=action.value,
            actor_id=actor_id,
            actor_type=actor_type,
            case_id=case_id,
            entity_type=entity_type,
            entity_id=entity_id,
            result=result.value,
            details_json=json.dumps(details) if details is not None else None,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            # Immutable hash chain - simplified for prototype
            previous_hash=previous_hash or self._get_last_hash(),
            hash=self._compute_hash(action, actor_id, case_id, details),
        )

        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)

        return entry

    def _get_last_hash(self) -> str:
        """Get hash of last audit entry for chain"""
        last = self.session.exec(
            select(AuditLog).order_by(AuditLog.timestamp.desc())
        ).first()
        return last.hash if last else "GENESIS"

    def _compute_hash(
        self,
        action: AuditAction,
        actor_id: str,
        case_id: Optional[str],
        details: Optional[Dict[str, Any]],
    ) -> str:
        """Compute hash for entry (simplified)"""
        import hashlib
        content = f"{action.value}|{actor_id}|{case_id}|{json.dumps(details or {}, sort_keys=True)}|{datetime.utcnow().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    # Convenience methods for common actions

    def log_case_created(self, actor_id: str, case_id: str, details: Optional[Dict] = None) -> AuditLog:
        return self.log(
            action=AuditAction.CASE_CREATED,
            actor_id=actor_id,
            case_id=case_id,
            details=details,
        )

    def log_case_updated(self, actor_id: str, case_id: str, details: Optional[Dict] = None) -> AuditLog:
        return self.log(
            action=AuditAction.CASE_UPDATED,
            actor_id=actor_id,
            case_id=case_id,
            details=details,
        )

    def log_document_uploaded(
        self,
        actor_id: str,
        case_id: str,
        document_id: str,
        document_type: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.DOCUMENT_UPLOADED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="DOCUMENT",
            entity_id=document_id,
            details={**(details or {}), "document_type": document_type},
        )

    def log_document_processed(
        self,
        actor_id: str,
        case_id: str,
        document_id: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.DOCUMENT_PROCESSED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="DOCUMENT",
            entity_id=document_id,
            details=details,
        )

    def log_ocr_completed(
        self,
        actor_id: str,
        case_id: str,
        document_id: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.OCR_COMPLETED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="DOCUMENT",
            entity_id=document_id,
            details=details,
        )

    def log_mrz_parsed(
        self,
        actor_id: str,
        case_id: str,
        document_id: str,
        valid: bool,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.MRZ_PARSED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="DOCUMENT",
            entity_id=document_id,
            result=AuditResult.SUCCESS if valid else AuditResult.FAILURE,
            details={**(details or {}), "mrz_valid": valid},
        )

    def log_barcode_read(
        self,
        actor_id: str,
        case_id: str,
        document_id: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.BARCODE_READ,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="DOCUMENT",
            entity_id=document_id,
            details=details,
        )

    def log_face_captured(
        self,
        actor_id: str,
        case_id: str,
        face_id: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.FACE_CAPTURED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="FACE",
            entity_id=face_id,
            details=details,
        )

    def log_face_verified(
        self,
        actor_id: str,
        case_id: str,
        face_id: str = None,
        document_id: str = None,
        match_result: str = "MATCH",
        match_score: float = 0.0,
        liveness_result: str = "LIVE",
        score: float = None,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        """Log face verification - supports both test API and production API"""
        details = details or {}
        if face_id:
            details["face_id"] = face_id
        if document_id:
            details["document_id"] = document_id
        if match_score is not None:
            details["match_score"] = match_score
        elif score is not None:
            details["match_score"] = score
        details["match_result"] = match_result
        details["liveness_result"] = liveness_result

        return self.log(
            action=AuditAction.FACE_VERIFIED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="FACE",
            entity_id=face_id or document_id,
            details=details,
        )

    def log_liveness_checked(
        self,
        actor_id: str,
        case_id: str,
        face_id: str,
        result: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.LIVENESS_CHECKED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="FACE",
            entity_id=face_id,
            details={**(details or {}), "liveness_result": result},
        )

    def log_tamper_checked(
        self,
        actor_id: str,
        case_id: str,
        document_id: str,
        tampered: bool,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.TAMPER_CHECKED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="DOCUMENT",
            entity_id=document_id,
            result=AuditResult.SUCCESS if not tampered else AuditResult.WARNING,
            details={**(details or {}), "tampered": tampered},
        )

    def log_validation_completed(
        self,
        actor_id: str,
        case_id: str,
        document_id: str,
        is_valid: bool,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.VALIDATION_COMPLETED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="DOCUMENT",
            entity_id=document_id,
            result=AuditResult.SUCCESS if is_valid else AuditResult.FAILURE,
            details=details,
        )

    def log_evidence_generated(
        self,
        actor_id: str,
        case_id: str,
        evidence_count: int = None,
        atom_types: list = None,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        """Log evidence generation - supports both test API and production API"""
        details = {**(details or {}), "evidence_count": evidence_count, "atom_types": atom_types}
        return self.log(
            action=AuditAction.EVIDENCE_GENERATED,
            actor_id=actor_id,
            case_id=case_id,
            details=details,
        )

    def log_fusion_completed(
        self,
        actor_id: str,
        case_id: str,
        recommendation: str = None,
        positive_score: float = None,
        negative_score: float = None,
        net_score: float = None,
        confidence: float = None,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        """Log fusion completion - supports both test API and production API"""
        details = {**(details or {}), "recommendation": recommendation, "positive_score": positive_score,
                   "negative_score": negative_score, "net_score": net_score, "confidence": confidence}
        return self.log(
            action=AuditAction.FUSION_COMPLETED,
            actor_id=actor_id,
            case_id=case_id,
            details=details,
        )

    def log_recommendation_viewed(
        self,
        actor_id: str,
        case_id: str,
        recommendation: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.RECOMMENDATION_VIEWED,
            actor_id=actor_id,
            case_id=case_id,
            details={**(details or {}), "recommendation": recommendation},
        )

    def log_officer_decision(
        self,
        actor_id: str = None,
        officer_id: str = None,
        case_id: str = None,
        decision: str = None,
        rationale: str = None,
        reason: str = None,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        """Log officer decision - supports both test API (officer_id, reason) and production API (actor_id, rationale)"""
        return self.log(
            action=AuditAction.OFFICER_DECISION,
            actor_id=actor_id or officer_id,
            case_id=case_id,
            details={**(details or {}), "decision": decision, "rationale": rationale or reason},
        )

    def log_case_closed(
        self,
        actor_id: str,
        case_id: str,
        final_decision: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.CASE_CLOSED,
            actor_id=actor_id,
            case_id=case_id,
            details={**(details or {}), "final_decision": final_decision},
        )

    def log_status_check_requested(
        self,
        actor_id: str,
        case_id: str,
        status_type: str,
        entity_identifier: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.STATUS_CHECK_REQUESTED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="STATUS_CHECK",
            entity_id=f"{status_type}:{entity_identifier}",
            details={**(details or {}), "status_type": status_type, "entity": entity_identifier},
        )

    def log_status_check_completed(
        self,
        actor_id: str,
        case_id: str,
        status_type: str,
        entity_identifier: str,
        status: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.STATUS_CHECK_COMPLETED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="STATUS_CHECK",
            entity_id=f"{status_type}:{entity_identifier}",
            details={**(details or {}), "status_type": status_type, "entity": entity_identifier, "status": status},
        )

    def log_status_check(
        self,
        actor_id: str,
        case_id: str,
        status_type: str,
        entity_identifier: str,
        result: str,
        freshness: str = None,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        """Log status check - combined method for tests"""
        details = {**(details or {}), "status_type": status_type, "entity": entity_identifier, "status": result}
        if freshness:
            details["freshness"] = freshness
        return self.log(
            action=AuditAction.STATUS_CHECK_COMPLETED,
            actor_id=actor_id,
            case_id=case_id,
            entity_type="STATUS_CHECK",
            entity_id=f"{status_type}:{entity_identifier}",
            details=details,
        )

    def log_sync_triggered(
        self,
        actor_id: str,
        case_id: Optional[str],
        operation_type: str,
        priority: str = "NORMAL",
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.SYNC_TRIGGERED,
            actor_id=actor_id,
            case_id=case_id,
            details={**(details or {}), "operation_type": operation_type, "priority": priority},
        )

    def log_sync_completed(
        self,
        actor_id: str,
        case_id: Optional[str],
        operation_type: str,
        success: bool,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.SYNC_COMPLETED,
            actor_id=actor_id,
            case_id=case_id,
            result=AuditResult.SUCCESS if success else AuditResult.FAILURE,
            details={**(details or {}), "operation_type": operation_type, "success": success},
        )

    def log_rule_set_updated(
        self,
        actor_id: str,
        version: str = None,
        rule_set_id: str = None,
        changes: list = None,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        """Log rule set update - supports both test API and production API"""
        details = {**(details or {}), "version": version, "rule_set_id": rule_set_id, "changes": changes}
        return self.log(
            action=AuditAction.RULE_SET_UPDATED,
            actor_id=actor_id,
            entity_type="RULE_SET",
            entity_id=rule_set_id,
            details=details,
        )

    def log_model_updated(
        self,
        actor_id: str,
        model_name: str,
        version: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.MODEL_UPDATED,
            actor_id=actor_id,
            details={**(details or {}), "model_name": model_name, "version": version},
        )

    def log_system_error(
        self,
        actor_id: str,
        case_id: Optional[str],
        error: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.SYSTEM_ERROR,
            actor_id=actor_id,
            case_id=case_id,
            result=AuditResult.FAILURE,
            details={**(details or {}), "error": error},
        )

    def log_access_denied(
        self,
        actor_id: str,
        resource: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.ACCESS_DENIED,
            actor_id=actor_id,
            result=AuditResult.FAILURE,
            details={**(details or {}), "resource": resource},
        )

    def log_export_requested(
        self,
        actor_id: str,
        case_id: str,
        format: str,
        details: Optional[Dict] = None,
    ) -> AuditLog:
        return self.log(
            action=AuditAction.EXPORT_REQUESTED,
            actor_id=actor_id,
            case_id=case_id,
            details={**(details or {}), "format": format},
        )

    def log_action(
        self,
        case_id: str,
        action: str,
        actor_id: str,
        actor_type: str = "OFFICER",
        result: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        previous_hash: Optional[str] = None,
    ) -> AuditLog:
        """Convenience method matching test API"""
        from app.models.audit import AuditAction, AuditResult
        return self.log(
            action=AuditAction(action),
            actor_id=actor_id,
            actor_type=actor_type,
            case_id=case_id,
            result=AuditResult(result),
            details=details,
            previous_hash=previous_hash,
        )

    # Query methods

    def get_case_audit_trail(self, case_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit trail for a case"""
        return self.session.exec(
            select(AuditLog)
            .where(AuditLog.case_id == case_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        ).all()

    def get_actor_audit_trail(self, actor_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit trail for an actor"""
        return self.session.exec(
            select(AuditLog)
            .where(AuditLog.actor_id == actor_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        ).all()

    def get_audit_trail(
        self,
        case_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get filtered audit trail"""
        query = select(AuditLog)

        if case_id:
            query = query.where(AuditLog.case_id == case_id)
        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)
        if action:
            query = query.where(AuditLog.action == action.value)
        if start_time:
            query = query.where(AuditLog.timestamp >= start_time)
        if end_time:
            query = query.where(AuditLog.timestamp <= end_time)

        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        return self.session.exec(query).all()

    def verify_chain(self, case_id: Optional[str] = None):
        """Verify audit chain integrity - returns object with attributes for test compatibility"""
        from types import SimpleNamespace
        query = select(AuditLog).order_by(AuditLog.timestamp.asc())
        if case_id:
            query = query.where(AuditLog.case_id == case_id)

        entries = self.session.exec(query).all()

        broken_links = []
        prev_hash = "GENESIS"

        for entry in entries:
            expected_prev = prev_hash
            actual_prev = entry.previous_hash or "GENESIS"  # Treat None as GENESIS for first entry
            if actual_prev != expected_prev:
                broken_links.append({
                    "entry_id": entry.id,
                    "expected": expected_prev,
                    "actual": actual_prev,
                })
            prev_hash = entry.hash

        return SimpleNamespace(
            total_entries=len(entries),
            broken_links=len(broken_links),
            details=broken_links,
            intact=len(broken_links) == 0,
        )


def log_audit(
    session: Session,
    action: AuditAction,
    actor_id: str,
    **kwargs,
) -> AuditLog:
    """Convenience function"""
    logger = AuditLogger(session)
    return logger.log(action, actor_id, **kwargs)


def log_action(
    session: Session,
    case_id: str,
    action: str,
    actor_id: str,
    actor_type: str = "OFFICER",
    result: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Convenience function matching test API"""
    logger = AuditLogger(session)
    from app.models.audit import AuditAction, AuditResult
    return logger.log(
        action=AuditAction(action),
        actor_id=actor_id,
        actor_type=actor_type,
        case_id=case_id,
        result=AuditResult(result),
        details=details,
    )