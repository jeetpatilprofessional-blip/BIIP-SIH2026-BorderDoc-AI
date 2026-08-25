# BIIP-SIH2026 Sync API
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime

from app.core.database import get_session
from app.models.sync_queue import SyncQueue, SyncStatus, SyncOperation
from app.schemas.sync import SyncStatusResponse, SyncQueueItem, SyncTrigger, SyncResult

router = APIRouter()


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(session: Session = Depends(get_session)):
    """Get sync queue status"""
    items = session.exec(
        select(SyncQueue).order_by(SyncQueue.created_at.desc())
    ).all()

    pending = sum(1 for i in items if i.status == SyncStatus.PENDING)
    in_progress = sum(1 for i in items if i.status == SyncStatus.IN_PROGRESS)
    completed = sum(1 for i in items if i.status == SyncStatus.COMPLETED)
    failed = sum(1 for i in items if i.status == SyncStatus.FAILED)
    conflict = sum(1 for i in items if i.status == SyncStatus.CONFLICT)

    last_sync = session.exec(
        select(SyncQueue)
        .where(SyncQueue.status == SyncStatus.COMPLETED)
        .order_by(SyncQueue.completed_at.desc())
    ).first()

    return SyncStatusResponse(
        pending=pending,
        in_progress=in_progress,
        completed=completed,
        failed=failed,
        conflict=conflict,
        total=len(items),
        items=[SyncQueueItem.model_validate(i) for i in items],
        last_sync_at=last_sync.completed_at if last_sync else None,
    )


@router.post("/trigger", response_model=SyncResult)
async def trigger_sync(
    trigger: SyncTrigger,
    session: Session = Depends(get_session),
):
    """Trigger synchronization with central service"""
    # Get pending items
    query = select(SyncQueue).where(SyncQueue.status == SyncStatus.PENDING)

    if trigger.operation_types:
        query = query.where(SyncQueue.operation.in_(trigger.operation_types))

    pending_items = session.exec(query.limit(50)).all()

    if not pending_items:
        return SyncResult(
            success=True,
            synced_count=0,
            failed_count=0,
            conflicts=[],
            message="No pending items to sync",
        )

    synced = 0
    failed = 0
    conflicts = []

    for item in pending_items:
        item.status = SyncStatus.IN_PROGRESS
        item.attempts += 1
        item.updated_at = datetime.utcnow()
        session.add(item)

        try:
            # TODO: Actual sync logic - call central service
            # For now, simulate success
            await simulate_sync(item, session)

            item.status = SyncStatus.COMPLETED
            item.completed_at = datetime.utcnow()
            synced += 1
        except Exception as e:
            item.last_error = str(e)
            if item.attempts >= item.max_attempts:
                item.status = SyncStatus.FAILED
            else:
                item.status = SyncStatus.PENDING
            failed += 1

        item.updated_at = datetime.utcnow()
        session.add(item)

    session.commit()

    return SyncResult(
        success=failed == 0,
        synced_count=synced,
        failed_count=failed,
        conflicts=conflicts,
        message=f"Synced {synced} items, {failed} failed",
    )


async def simulate_sync(item: SyncQueue, session: Session):
    """Simulate sync with central service"""
    # In real implementation, this would:
    # 1. Call central service API
    # 2. Handle response
    # 3. Update local cache
    # 4. Handle conflicts

    import json
    payload = json.loads(item.payload)

    # Simulate network delay
    import asyncio
    await asyncio.sleep(0.1)

    # For demo, always succeed
    return True