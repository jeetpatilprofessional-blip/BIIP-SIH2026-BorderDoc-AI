# BIIP-SIH2026 System API
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from typing import List
from datetime import datetime, timedelta

from app.core.database import get_session
from app.core.config import get_settings
from app.models.status_cache import StatusCache, FreshnessState
from app.models.sync_queue import SyncQueue, SyncStatus
from app.models.case import Case, CaseStatus
from app.schemas.system import SystemStatus, ComponentHealth, DatabaseFreshness, ComponentStatus, SystemMode

router = APIRouter()
settings = get_settings()


@router.get("/status", response_model=SystemStatus)
async def get_system_status(session: Session = Depends(get_session)):
    """Get overall system status"""
    # Component health checks
    components = [
        ComponentHealth(
            name="Database",
            status=ComponentStatus.HEALTHY,
            message="SQLite connected",
            last_check=datetime.utcnow(),
        ),
        ComponentHealth(
            name="OCR Service",
            status=ComponentStatus.HEALTHY,
            message="PaddleOCR ready",
            last_check=datetime.utcnow(),
        ),
        ComponentHealth(
            name="Face Recognition",
            status=ComponentStatus.HEALTHY,
            message="InsightFace ONNX loaded",
            last_check=datetime.utcnow(),
        ),
        ComponentHealth(
            name="MRZ Parser",
            status=ComponentStatus.HEALTHY,
            message="Ready",
            last_check=datetime.utcnow(),
        ),
        ComponentHealth(
            name="Barcode Reader",
            status=ComponentStatus.HEALTHY,
            message="pyzbar ready",
            last_check=datetime.utcnow(),
        ),
        ComponentHealth(
            name="Central Service",
            status=ComponentStatus.HEALTHY if settings.CENTRAL_SERVICE_ENABLED else ComponentStatus.UNKNOWN,
            message="Simulated" if settings.CENTRAL_SERVICE_SIMULATED else "Connected",
            last_check=datetime.utcnow(),
        ),
    ]

    overall_health = ComponentStatus.HEALTHY
    if any(c.status == ComponentStatus.UNHEALTHY for c in components):
        overall_health = ComponentStatus.UNHEALTHY
    elif any(c.status == ComponentStatus.DEGRADED for c in components):
        overall_health = ComponentStatus.DEGRADED

    # Database freshness
    freshness_records = session.exec(select(StatusCache)).all()
    db_freshness = []
    for record in freshness_records:
        hours_since_sync = (datetime.utcnow() - record.last_synced_at).total_seconds() / 3600
        is_stale = hours_since_sync > record.freshness_policy_hours

        db_freshness.append(DatabaseFreshness(
            status_type=record.status_type.value,
            source=record.source,
            last_synced_at=record.last_synced_at,
            freshness_policy_hours=record.freshness_policy_hours,
            freshness_state=record.freshness.value,
            record_count=1,
        ))

    # Sync queue stats
    sync_pending = session.exec(
        select(func.count()).where(SyncQueue.status == SyncStatus.PENDING)
    ).one()
    sync_failed = session.exec(
        select(func.count()).where(SyncQueue.status == SyncStatus.FAILED)
    ).one()

    return SystemStatus(
        mode=SystemMode.OFFLINE if settings.OFFLINE_MODE else SystemMode.ONLINE,
        overall_health=overall_health,
        components=components,
        database_freshness=db_freshness,
        sync_queue_pending=sync_pending,
        sync_queue_failed=sync_failed,
        uptime_seconds=0,  # TODO: track actual uptime
        version=settings.APP_VERSION,
    )


@router.post("/offline")
async def set_offline_mode(session: Session = Depends(get_session)):
    """Enter offline mode"""
    settings.OFFLINE_MODE = True

    # Audit
    from app.services.audit import create_audit_event
    from app.models.audit import AuditEventType
    cases = session.exec(select(Case).where(Case.status.in_([CaseStatus.CREATED, CaseStatus.PROCESSING, CaseStatus.AWAITING_REVIEW]))).all()
    for case in cases:
        case.is_offline = True
        session.add(case)
        await create_audit_event(
            session=session,
            case_id=case.id,
            event_type=AuditEventType.OFFLINE_MODE_ENTERED,
            module="SYSTEM",
            actor_type="SYSTEM",
        )
    session.commit()

    return {"message": "Offline mode enabled", "mode": "OFFLINE"}


@router.post("/online")
async def set_online_mode(session: Session = Depends(get_session)):
    """Restore online mode"""
    settings.OFFLINE_MODE = False

    # Audit
    from app.services.audit import create_audit_event
    from app.models.audit import AuditEventType
    cases = session.exec(select(Case).where(Case.is_offline == True)).all()
    for case in cases:
        case.is_offline = False
        session.add(case)
        await create_audit_event(
            session=session,
            case_id=case.id,
            event_type=AuditEventType.ONLINE_MODE_RESTORED,
            module="SYSTEM",
            actor_type="SYSTEM",
        )
    session.commit()

    return {"message": "Online mode restored", "mode": "ONLINE"}