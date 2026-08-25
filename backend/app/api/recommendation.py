# BIIP-SIH2026 Recommendation API
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any
from datetime import datetime

from app.core.database import get_session
from app.models.case import Case, RecommendationType
from app.models.evidence import EvidenceAtom, EvidenceSeverity, EvidenceSource, FreshnessState
from app.models.identity_graph import IdentityNode, IdentityEdge, NodeType, EdgeType
from app.schemas.recommendation import RecommendationRead, RecommendationDetail, EvidenceSummaryItem
from app.services.evidence.fusion import generate_recommendation
from app.services.evidence.models import EvidenceContribution, EvidenceSeverity as FusionEvidenceSeverity, FreshnessState as FusionFreshnessState

router = APIRouter()


def _fusion_to_recommendation_read(fusion) -> RecommendationRead:
    """Convert FusionResult to RecommendationRead schema"""
    supporting = []
    contradicting = []

    for contrib in fusion.supporting_evidence:
        if contrib.contribution >= 0:
            supporting.append(EvidenceSummaryItem(
                evidence_type=contrib.evidence_type,
                source=contrib.source,
                severity=contrib.severity.value,
                confidence=contrib.confidence,
                description=contrib.description,
                explanation=contrib.explanation,
                entities=contrib.entities,
                freshness=contrib.freshness.value,
            ))
        else:
            contradicting.append(EvidenceSummaryItem(
                evidence_type=contrib.evidence_type,
                source=contrib.source,
                severity=contrib.severity.value,
                confidence=contrib.confidence,
                description=contrib.description,
                explanation=contrib.explanation,
                entities=contrib.entities,
                freshness=contrib.freshness.value,
            ))

    for contrib in fusion.contradicting_evidence:
        if contrib.contribution >= 0:
            supporting.append(EvidenceSummaryItem(
                evidence_type=contrib.evidence_type,
                source=contrib.source,
                severity=contrib.severity.value,
                confidence=contrib.confidence,
                description=contrib.description,
                explanation=contrib.explanation,
                entities=contrib.entities,
                freshness=contrib.freshness.value,
            ))
        else:
            contradicting.append(EvidenceSummaryItem(
                evidence_type=contrib.evidence_type,
                source=contrib.source,
                severity=contrib.severity.value,
                confidence=contrib.confidence,
                description=contrib.description,
                explanation=contrib.explanation,
                entities=contrib.entities,
                freshness=contrib.freshness.value,
            ))

    return RecommendationRead(
        case_id=fusion.case_id,
        recommendation=fusion.recommendation,
        confidence=fusion.confidence,
        reasoning=fusion.reasoning,
        primary_reasons=fusion.primary_reasons,
        supporting_evidence=supporting,
        data_freshness_warnings=fusion.data_freshness_warnings,
        limitations=fusion.limitations,
        recommended_action=fusion.recommended_action,
        created_at=fusion.generated_at,
        net_score=getattr(fusion, "net_score", 0.0),
        critical_flags=getattr(fusion, "critical_flags", []),
        freshness_breakdown=getattr(fusion, "freshness_breakdown", {}),
    )


@router.get("/{case_id}/recommendation", response_model=RecommendationRead)
async def get_recommendation(case_id: str, session: Session = Depends(get_session)):
    """Get the screening recommendation for a case"""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Generate recommendation if not already present
    if case.recommendation is None:
        recommendation = generate_recommendation(case_id, session)
        case.recommendation = recommendation.recommendation
        case.recommendation_confidence = recommendation.confidence
        case.recommendation_reasoning = recommendation.reasoning
        case.updated_at = datetime.utcnow()
        session.add(case)
        session.commit()
    else:
        recommendation = generate_recommendation(case_id, session)

    return _fusion_to_recommendation_read(recommendation)


@router.get("/{case_id}/recommendation/detail", response_model=RecommendationDetail)
@router.get("/{case_id}/evidence/fusion", response_model=RecommendationDetail)
@router.get("/{case_id}/fusion", response_model=RecommendationDetail)
async def get_recommendation_detail(case_id: str, session: Session = Depends(get_session)):

    """Get detailed recommendation with all evidence and graph"""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    fusion = generate_recommendation(case_id, session)
    recommendation_read = _fusion_to_recommendation_read(fusion)

    # Get all evidence atoms
    evidence_atoms = session.exec(
        select(EvidenceAtom).where(EvidenceAtom.case_id == case_id)
    ).all()

    # Get identity graph
    nodes = session.exec(
        select(IdentityNode).where(IdentityNode.case_id == case_id)
    ).all()
    edges = session.exec(
        select(IdentityEdge).where(IdentityEdge.case_id == case_id)
    ).all()

    # Build graph summary
    graph_summary = {
        "nodes": [
            {
                "id": n.id,
                "type": n.node_type.value,
                "entity_id": n.entity_id,
                "label": n.label,
            }
            for n in nodes
        ],
        "edges": [
            {
                "id": e.id,
                "source": e.source_node_id,
                "target": e.target_node_id,
                "type": e.edge_type.value,
                "weight": e.weight,
            }
            for e in edges
        ],
    }

    # Freshness summary
    freshness_summary = {}
    for fs in FreshnessState:
        count = sum(1 for ea in evidence_atoms if ea.freshness == fs)
        freshness_summary[fs.value] = count

    return RecommendationDetail(
        case_id=fusion.case_id,
        recommendation=fusion.recommendation,
        confidence=fusion.confidence,
        net_score=getattr(fusion, "net_score", 0.0),
        critical_flags=getattr(fusion, "critical_flags", []),
        freshness_breakdown=getattr(fusion, "freshness_breakdown", {}),
        reasoning=fusion.reasoning,
        primary_reasons=fusion.primary_reasons,
        supporting_evidence=recommendation_read.supporting_evidence,
        data_freshness_warnings=fusion.data_freshness_warnings,
        limitations=fusion.limitations,
        recommended_action=fusion.recommended_action,
        created_at=fusion.generated_at,
        evidence_atoms=[ea.model_dump() for ea in evidence_atoms],
        identity_graph_summary=graph_summary,
        freshness_summary=freshness_summary,
        recommendation_read=recommendation_read,
    )