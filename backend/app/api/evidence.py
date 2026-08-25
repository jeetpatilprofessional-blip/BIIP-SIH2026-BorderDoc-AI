# BIIP-SIH2026 Evidence API
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime

from app.core.database import get_session
from app.models.evidence import EvidenceAtom, EvidenceSeverity, EvidenceSource, FreshnessState
from app.models.case import Case
from app.schemas.evidence import EvidenceAtomRead, EvidenceSummary

router = APIRouter()


@router.get("/{case_id}/evidence", response_model=List[EvidenceAtomRead])
async def get_evidence(
    case_id: str,
    severity: Optional[EvidenceSeverity] = None,
    source: Optional[EvidenceSource] = None,
    freshness: Optional[FreshnessState] = None,
    session: Session = Depends(get_session),
):
    """Get all evidence atoms for a case"""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    query = select(EvidenceAtom).where(EvidenceAtom.case_id == case_id)

    if severity:
        query = query.where(EvidenceAtom.severity == severity)
    if source:
        query = query.where(EvidenceAtom.source == source)
    if freshness:
        query = query.where(EvidenceAtom.freshness == freshness)

    evidence = session.exec(query.order_by(EvidenceAtom.created_at.desc())).all()
    return evidence


@router.get("/{case_id}/evidence/summary", response_model=EvidenceSummary)
async def get_evidence_summary(case_id: str, session: Session = Depends(get_session)):
    """Get evidence summary for a case"""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    all_evidence = session.exec(
        select(EvidenceAtom).where(EvidenceAtom.case_id == case_id)
    ).all()

    by_severity = {}
    by_source = {}
    by_freshness = {}
    critical_count = 0
    high_count = 0
    stale_count = 0
    unavailable_count = 0

    for e in all_evidence:
        by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1
        by_source[e.source.value] = by_source.get(e.source.value, 0) + 1
        by_freshness[e.freshness.value] = by_freshness.get(e.freshness.value, 0) + 1

        if e.severity == EvidenceSeverity.CRITICAL:
            critical_count += 1
        elif e.severity == EvidenceSeverity.HIGH:
            high_count += 1
        if e.freshness == FreshnessState.VERIFIED_STALE:
            stale_count += 1
        elif e.freshness == FreshnessState.UNAVAILABLE:
            unavailable_count += 1

    return EvidenceSummary(
        total=len(all_evidence),
        by_severity=by_severity,
        by_source=by_source,
        by_freshness=by_freshness,
        critical_count=critical_count,
        high_count=high_count,
        stale_count=stale_count,
        unavailable_count=unavailable_count,
    )