# BIIP-SIH2026 Audit API
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any
from datetime import datetime

from app.core.database import get_session
from app.models.audit import AuditEvent, AuditLog
from app.services.audit.logger import AuditLogger

router = APIRouter()


@router.get("/{case_id}", response_model=Dict[str, Any])
@router.get("/case/{case_id}", response_model=Dict[str, Any])
async def get_case_audit(case_id: str, session: Session = Depends(get_session)):

    """Get audit trail for a case with chain verification"""
    logger = AuditLogger(session)

    # Get audit trail
    audit_entries = logger.get_case_audit_trail(case_id, limit=500)

    # Verify chain
    chain_verification = logger.verify_chain(case_id)

    # Also get AuditEvent records (from the event system)
    audit_events = session.exec(
        select(AuditEvent)
        .where(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.timestamp.desc())
    ).all()

    # Format audit log entries
    formatted_log = []
    for entry in audit_entries:
        formatted_log.append({
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "action": entry.action,
            "actor_id": entry.actor_id,
            "actor_type": entry.actor_type,
            "case_id": entry.case_id,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "result": entry.result,
            "details": entry.details,
            "previous_hash": entry.previous_hash,
            "hash": entry.hash,
        })

    # Format audit events
    formatted_events = []
    for event in audit_events:
        import json
        formatted_events.append({
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type.value,
            "module": event.module,
            "details": json.loads(event.details) if event.details else None,
            "actor_type": event.actor_type,
            "actor_id": event.actor_id,
        })

    return {
        "case_id": case_id,
        "audit_log": formatted_log,
        "audit_events": formatted_events,
        "chain_verified": chain_verification.intact,
        "chain_details": {
            "total_entries": chain_verification.total_entries,
            "broken_links": chain_verification.broken_links,
            "details": chain_verification.details,
        }
    }


@router.get("/{case_id}/verify", response_model=Dict[str, Any])
async def verify_audit_chain(case_id: str, session: Session = Depends(get_session)):
    """Verify audit chain integrity for a case"""
    logger = AuditLogger(session)
    verification = logger.verify_chain(case_id)

    return {
        "case_id": case_id,
        "chain_verified": verification.intact,
        "total_entries": verification.total_entries,
        "broken_links": verification.broken_links,
        "details": verification.details,
    }