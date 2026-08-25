# BIIP-SIH2026 Cases API
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_session
from app.models.case import Case, CaseStatus, RecommendationType
from app.schemas.case import CaseCreate, CaseRead, CaseList, CaseUpdate
from app.services.audit import create_audit_event
from app.models.audit import AuditEventType

router = APIRouter()


@router.post("", response_model=CaseRead, status_code=201)
async def create_case(
    case_data: CaseCreate,
    session: Session = Depends(get_session),
):
    """Create a new screening case"""
    # Generate case number
    case_number = f"BIIP-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

    case = Case(
        case_number=case_number,
        status=CaseStatus.CREATED,
        officer_id=case_data.officer_id,
        metadata_json=str(case_data.metadata) if case_data.metadata else None,
    )

    session.add(case)
    session.commit()
    session.refresh(case)

    # Audit
    await create_audit_event(
        session=session,
        case_id=case.id,
        event_type=AuditEventType.CASE_CREATED,
        module="CASES",
        details={"case_number": case_number},
        actor_type="SYSTEM",
    )

    return case


@router.get("", response_model=CaseList)
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[CaseStatus] = None,
    session: Session = Depends(get_session),
):
    """List cases with pagination"""
    query = select(Case)

    if status:
        query = query.where(Case.status == status)

    # Count total
    total = session.exec(select(func.count()).select_from(query.subquery())).one()

    # Paginate
    cases = session.exec(
        query.order_by(Case.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return CaseList(cases=cases, total=total, page=page, page_size=page_size)


@router.get("/{case_id}", response_model=CaseRead)
async def get_case(case_id: str, session: Session = Depends(get_session)):
    """Get case by ID"""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/{case_id}", response_model=CaseRead)
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    session: Session = Depends(get_session),
):
    """Update case"""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    update_data = case_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "metadata" and value is not None:
            setattr(case, "metadata_json", str(value))
        else:
            setattr(case, field, value)

    case.updated_at = datetime.utcnow()
    session.add(case)
    session.commit()
    session.refresh(case)

    return case


@router.post("/{case_id}/complete")
async def complete_case(case_id: str, session: Session = Depends(get_session)):
    """Mark case as completed"""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = CaseStatus.COMPLETED
    case.completed_at = datetime.utcnow()
    case.updated_at = datetime.utcnow()
    session.add(case)
    session.commit()

    return {"message": "Case completed", "case_id": case_id}