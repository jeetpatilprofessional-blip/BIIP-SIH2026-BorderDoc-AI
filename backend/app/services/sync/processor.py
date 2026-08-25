# BIIP-SIH2026 Sync Processor
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
import json

from app.services.sync.models import (
    SyncQueueItem,
    SyncStatus,
    SyncOperationType,
    SyncPriority,
    SyncResult,
    CentralStatusResponse,
    CentralSyncRequest,
    CentralSyncResponse,
    ConnectivityStatus,
    SIMULATED_WATCHLIST,
    SIMULATED_VISA_STATUS,
    SIMULATED_PASSPORT_STATUS,
)
from app.models.sync_queue import SyncQueue, SyncOperation
from app.models.status_cache import StatusCache, StatusType, FreshnessState as CacheFreshnessState
from app.models.case import Case
from app.models.evidence import EvidenceAtom
from app.models.face_result import FaceResult
from app.core.config import get_settings
from app.core.database import get_session


class SyncProcessor:
    """Process sync queue items"""

    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()
        self.is_running = False

    def enqueue(
        self,
        operation_type: SyncOperationType,
        case_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        priority: SyncPriority = SyncPriority.NORMAL,
        idempotency_key: Optional[str] = None,
    ) -> SyncQueue:
        """Add item to sync queue"""

        # Map SyncOperationType to SyncOperation enum
        op_map = {
            SyncOperationType.STATUS_CHECK: SyncOperation.STATUS_REFRESH,
            SyncOperationType.CASE_SYNC: SyncOperation.CASE_UPDATE,
            SyncOperationType.EVIDENCE_SYNC: SyncOperation.EVIDENCE_SYNC,
            SyncOperationType.FACE_EMBEDDING_SYNC: SyncOperation.EVIDENCE_SYNC,
            SyncOperationType.RULE_UPDATE: SyncOperation.AUDIT_SYNC,
            SyncOperationType.MODEL_UPDATE: SyncOperation.AUDIT_SYNC,
        }

        item = SyncQueue(
            id=str(uuid.uuid4()),
            operation=op_map.get(operation_type, SyncOperation.STATUS_REFRESH),
            entity_type="case" if case_id else "status",
            entity_id=case_id or payload.get("entity_identifier", "unknown") if payload else "unknown",
            payload=json.dumps(payload or {}),
            status=SyncStatus.PENDING.value,
            attempts=0,
            max_attempts=3,
        )

        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)

        return item

    def enqueue_status_check(
        self,
        case_id: str,
        status_type: StatusType,
        entity_identifier: str,
        priority: SyncPriority = SyncPriority.HIGH,
    ) -> SyncQueue:
        """Enqueue a status check operation"""
        return self.enqueue(
            operation_type=SyncOperationType.STATUS_CHECK,
            case_id=case_id,
            payload={
                "status_type": status_type.value,
                "entity_identifier": entity_identifier,
            },
            priority=priority,
            idempotency_key=f"status_{case_id}_{status_type.value}_{entity_identifier}",
        )

    def enqueue_case_sync(self, case_id: str, priority: SyncPriority = SyncPriority.NORMAL) -> SyncQueue:
        """Enqueue full case sync"""
        return self.enqueue(
            operation_type=SyncOperationType.CASE_SYNC,
            case_id=case_id,
            priority=priority,
            idempotency_key=f"case_sync_{case_id}",
        )

    def process_queue(self, batch_size: int = 10) -> List[SyncResult]:
        """Process pending sync items"""
        results = []

        # Get pending items ordered by creation time (SyncQueue doesn't have priority field)
        pending = self.session.exec(
            select(SyncQueue)
            .where(SyncQueue.status == SyncStatus.PENDING.value)
            .order_by(SyncQueue.created_at)
        ).all()

        for item in pending[:batch_size]:
            result = self._process_item(item)
            results.append(result)

        return results

    def _process_item(self, item: SyncQueue) -> SyncResult:
        """Process a single sync queue item"""
        item.status = SyncStatus.IN_PROGRESS.value
        item.attempts += 1
        self.session.add(item)
        self.session.commit()

        try:
            if item.operation == SyncOperation.STATUS_REFRESH:
                result = self._process_status_check(item)
            elif item.operation == SyncOperation.CASE_UPDATE:
                result = self._process_case_sync(item)
            elif item.operation == SyncOperation.EVIDENCE_SYNC:
                result = self._process_evidence_sync(item)
            elif item.operation == SyncOperation.OFFICER_ACTION:
                result = self._process_face_embedding_sync(item)
            elif item.operation == SyncOperation.AUDIT_SYNC:
                result = self._process_rule_update(item)
            else:
                result = SyncResult(
                    success=False,
                    operation_id=item.id,
                    message=f"Unknown operation type: {item.operation}",
                )

            if result.success:
                item.status = SyncStatus.COMPLETED.value
            else:
                item.status = SyncStatus.FAILED.value
                item.last_error = result.message

            item.completed_at = datetime.utcnow()
            item.updated_at = datetime.utcnow()
            self.session.add(item)
            self.session.commit()

            return result

        except Exception as e:
            item.status = SyncStatus.FAILED.value
            item.last_error = str(e)
            item.completed_at = datetime.utcnow()
            item.updated_at = datetime.utcnow()
            self.session.add(item)
            self.session.commit()

            return SyncResult(
                success=False,
                operation_id=item.id,
                message=f"Processing error: {e}",
            )

    def _process_status_check(self, item: SyncQueue) -> SyncResult:
        """Process status check - SIMULATED central service call"""
        payload = json.loads(item.payload) if item.payload else {}
        status_type = payload.get("status_type")
        entity_identifier = payload.get("entity_identifier")
        case_id = item.entity_id if item.entity_type == "case" else None

        if not status_type or not entity_identifier:
            return SyncResult(
                success=False,
                operation_id=item.id,
                message="Missing status_type or entity_identifier",
            )

        # SIMULATED: Call central service
        # In production: response = central_client.check_status(status_type, entity_identifier)
        response = self._simulate_central_status_check(status_type, entity_identifier)

        # Update local cache
        freshness = CacheFreshnessState.VERIFIED_FRESH
        is_adverse = response.status in ["REVOKED", "WATCHLISTED", "LOST", "STOLEN", "BLACKLISTED", "INVALID", "EXPIRED"]

        if is_adverse:
            freshness = CacheFreshnessState.CONFIRMED_ADVERSE

        # Determine policy hours
        policy_hours = 24
        if status_type == "WATCHLIST":
            policy_hours = self.settings.FRESHNESS_WATCHLIST_HOURS
        elif status_type == "VISA":
            policy_hours = self.settings.FRESHNESS_VISA_HOURS
        elif status_type == "PASSPORT":
            policy_hours = self.settings.FRESHNESS_PASSPORT_HOURS
        elif status_type == "NATIONAL_ID":
            policy_hours = self.settings.FRESHNESS_NATIONAL_ID_HOURS

        cache_record = StatusCache(
            case_id=case_id,
            status_type=StatusType(status_type),
            entity_identifier=entity_identifier,
            entity_subtype=None,
            status=response.status,
            freshness=freshness,
            last_synced_at=datetime.utcnow(),
            freshness_policy_hours=policy_hours,
            source=response.source,
            source_version=response.source_version,
            is_adverse=is_adverse,
            adverse_reason=response.adverse_reason,
        )

        self.session.add(cache_record)
        self.session.commit()

        return SyncResult(
            success=True,
            operation_id=item.id,
            message=f"Status check completed: {response.status}",
            details={
                "entity": entity_identifier,
                "status": response.status,
                "source": response.source,
                "freshness": freshness.value,
            },
            items_processed=1,
            server_timestamp=datetime.utcnow(),
        )

    def _process_case_sync(self, item: SyncQueue) -> SyncResult:
        """Process full case sync - SIMULATED"""
        # In production: send case data, evidence, embeddings to central
        # For now, simulate success

        return SyncResult(
            success=True,
            operation_id=item.id,
            message="Case sync completed (simulated)",
            details={"case_id": item.case_id},
            items_processed=1,
            server_timestamp=datetime.utcnow(),
        )

    def _process_evidence_sync(self, item: SyncQueue) -> SyncResult:
        """Process evidence sync - SIMULATED"""
        return SyncResult(
            success=True,
            operation_id=item.id,
            message="Evidence sync completed (simulated)",
            items_processed=1,
            server_timestamp=datetime.utcnow(),
        )

    def _process_face_embedding_sync(self, item: SyncQueue) -> SyncResult:
        """Process face embedding sync - SIMULATED"""
        return SyncResult(
            success=True,
            operation_id=item.id,
            message="Face embedding sync completed (simulated)",
            items_processed=1,
            server_timestamp=datetime.utcnow(),
        )

    def _process_rule_update(self, item: SyncQueue) -> SyncResult:
        """Process rule set update - SIMULATED"""
        return SyncResult(
            success=True,
            operation_id=item.id,
            message="Rule update completed (simulated)",
            details={"new_version": "1.1"},
            items_processed=1,
            server_timestamp=datetime.utcnow(),
        )

    def _process_model_update(self, item: SyncQueue) -> SyncResult:
        """Process model update - SIMULATED"""
        return SyncResult(
            success=True,
            operation_id=item.id,
            message="Model update completed (simulated)",
            items_processed=1,
            server_timestamp=datetime.utcnow(),
        )

    def _simulate_central_status_check(
        self,
        status_type: str,
        entity_identifier: str,
    ) -> CentralStatusResponse:
        """Simulate central service status check"""
        import random

        # Check simulated databases
        if status_type == "WATCHLIST":
            if entity_identifier in SIMULATED_WATCHLIST:
                data = SIMULATED_WATCHLIST[entity_identifier]
                return CentralStatusResponse(
                    entity_identifier=entity_identifier,
                    status_type=status_type,
                    status=data["status"],
                    source=data.get("source", "INTERPOL_SLTD"),
                    source_version="2024.1",
                    adverse_reason=data.get("reason"),
                    last_updated=datetime.utcnow(),
                    freshness_hours=0,
                )

        elif status_type == "VISA":
            if entity_identifier in SIMULATED_VISA_STATUS:
                data = SIMULATED_VISA_STATUS[entity_identifier]
                return CentralStatusResponse(
                    entity_identifier=entity_identifier,
                    status_type=status_type,
                    status=data["status"],
                    source=data.get("source", "VISA_SYSTEM"),
                    source_version="2024.1",
                    adverse_reason=data.get("reason"),
                    last_updated=datetime.utcnow(),
                    freshness_hours=0,
                )

        elif status_type == "PASSPORT":
            if entity_identifier in SIMULATED_PASSPORT_STATUS:
                data = SIMULATED_PASSPORT_STATUS[entity_identifier]
                return CentralStatusResponse(
                    entity_identifier=entity_identifier,
                    status_type=status_type,
                    status=data["status"],
                    source=data.get("source", "PASSPORT_REGISTRY"),
                    source_version="2024.1",
                    adverse_reason=data.get("reason"),
                    last_updated=datetime.utcnow(),
                    freshness_hours=0,
                )

        # Default: CLEAN
        source_map = {
            "WATCHLIST": "NATIONAL_DB",
            "VISA": "VISA_SYSTEM",
            "PASSPORT": "PASSPORT_REGISTRY",
            "NATIONAL_ID": "NATIONAL_ID_REGISTRY",
        }

        return CentralStatusResponse(
            entity_identifier=entity_identifier,
            status_type=status_type,
            status="CLEAN",
            source=source_map.get(status_type, "UNKNOWN"),
            source_version="2024.1",
            last_updated=datetime.utcnow(),
            freshness_hours=0,
        )

    def retry_failed(self, max_retries: int = 3) -> int:
        """Retry failed items that haven't exceeded max retries"""
        failed = self.session.exec(
            select(SyncQueue).where(
                SyncQueue.status == SyncStatus.FAILED.value,
                SyncQueue.retry_count < max_retries,
            )
        ).all()

        count = 0
        for item in failed:
            item.status = SyncStatus.PENDING.value
            item.last_error = None
            self.session.add(item)
            count += 1

        self.session.commit()
        return count

    def get_connectivity_status(self) -> ConnectivityStatus:
        """Get current connectivity status"""
        pending_count = self.session.exec(
            select(SyncQueue).where(SyncQueue.status == SyncStatus.PENDING.value)
        ).all()

        failed_count = self.session.exec(
            select(SyncQueue).where(SyncQueue.status == SyncStatus.FAILED.value)
        ).all()

        last_sync = self.session.exec(
            select(SyncQueue)
            .where(SyncQueue.status == SyncStatus.COMPLETED.value)
            .order_by(SyncQueue.completed_at.desc())
        ).first()

        return ConnectivityStatus(
            is_online=True,  # SIMULATED: always online in prototype
            last_successful_sync=last_sync.completed_at if last_sync else None,
            pending_queue_size=len(pending_count),
            failed_queue_size=len(failed_count),
            estimated_backlog_hours=len(pending_count) * 0.1,
            central_endpoint=self.settings.CENTRAL_API_URL,
            last_check=datetime.utcnow(),
        )


class CentralServiceClient:
    """Client for communicating with central backend (SIMULATED)"""

    def __init__(self, settings=None, base_url: str = None):
        if isinstance(settings, str):
            # Backward compatibility: settings was passed as base_url string
            self.base_url = settings
            self.settings = None
        else:
            self.settings = settings or get_settings()
            self.base_url = base_url or self.settings.CENTRAL_API_URL

    async def check_status(
        self,
        status_type: str,
        entity_identifier: str,
    ) -> CentralStatusResponse:
        """Check status with central service"""
        # SIMULATED: In production, make HTTP request
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(...)
        return self._simulate_check(status_type, entity_identifier)

    async def sync_case(self, request: CentralSyncRequest) -> CentralSyncResponse:
        """Sync full case to central"""
        # SIMULATED
        return CentralSyncResponse(
            sync_id=str(uuid.uuid4()),
            status="ACCEPTED",
            server_timestamp=datetime.utcnow(),
        )

    async def pull_rules(self, version: str) -> Dict[str, Any]:
        """Pull updated rule sets"""
        return {"version": "1.1", "rules": {}}

    async def pull_models(self, model_names: List[str]) -> Dict[str, bytes]:
        """Pull updated model files"""
        return {}

    async def _simulate_check(self, status_type: str, entity_identifier: str) -> CentralStatusResponse:
        """Simulate central check"""
        processor = SyncProcessor(next(get_session()))
        return processor._simulate_central_status_check(status_type, entity_identifier)


def process_sync_queue(session: Session, batch_size: int = 10) -> List[SyncResult]:
    """Convenience function"""
    processor = SyncProcessor(session)
    return processor.process_queue(batch_size)


def enqueue_status_check(
    session: Session,
    case_id: str,
    status_type: StatusType,
    entity_identifier: str,
    priority: SyncPriority = SyncPriority.HIGH,
) -> SyncQueue:
    """Convenience function"""
    processor = SyncProcessor(session)
    return processor.enqueue_status_check(case_id, status_type, entity_identifier, priority)