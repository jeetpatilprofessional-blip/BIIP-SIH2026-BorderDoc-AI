# BIIP-SIH2026 Audit Service
from .logger import AuditLogger, log_audit
from app.models.audit import AuditEventType

__all__ = [
    "AuditLogger",
    "log_audit",
    "create_audit_event",
    "AuditEventType",
]


async def create_audit_event(
    session,
    case_id: str,
    event_type: AuditEventType,
    module: str,
    details: dict,
    actor_type: str = "SYSTEM",
    actor_id: str = None,
):
    """Create an audit event (compatible with existing API)"""
    logger = AuditLogger(session)
    return logger.log(
        action=event_type.value,
        actor_id=actor_id or "SYSTEM",
        actor_type=actor_type,
        case_id=case_id,
        details=details,
    )