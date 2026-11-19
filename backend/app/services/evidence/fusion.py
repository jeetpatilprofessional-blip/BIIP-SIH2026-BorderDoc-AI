# BIIP-SIH2026 Evidence Fusion Engine
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from collections import defaultdict
import ast

from app.services.evidence.models import (
    FusionResult,
    EvidenceContribution,
    RecommendationType,
    EvidenceSeverity,
    FreshnessState,
)
from app.models.evidence import EvidenceAtom, EvidenceSeverity as ModelEvidenceSeverity, FreshnessState as ModelFreshnessState
from app.models.case import Case


class EvidenceFusionEngine:
    """Explainable evidence fusion with additive contributions"""

    def __init__(self, session: Session):
        self.session = session

        # Severity weights
        self.severity_weights = {
            EvidenceSeverity.INFO: 0.2,
            EvidenceSeverity.LOW: 0.35,
            EvidenceSeverity.MEDIUM: 0.5,
            EvidenceSeverity.HIGH: 0.85,
            EvidenceSeverity.CRITICAL: 2.0,
        }



        # Freshness modifiers
        self.freshness_modifiers = {
            FreshnessState.VERIFIED_FRESH: 1.0,
            FreshnessState.VERIFIED_STALE: 0.6,
            FreshnessState.UNAVAILABLE: 0.3,
            FreshnessState.CONFIRMED_ADVERSE: 1.0,  # Adverse is always full weight
        }

        # Source reliability
        self.source_reliability = {
            "WATCHLIST": 0.95,
            "REVOCATION": 0.95,
            "FACE_VERIFICATION": 0.9,
            "MRZ": 0.95,
            "BARCODE": 0.85,
            "DOCUMENT_VALIDATION": 0.95,
            "TAMPER_ANALYSIS": 0.85,
            "IDENTITY_GRAPH": 0.85,
            "VISA_RULES": 0.9,
            "LIVENESS": 0.6,  # Prototype
            "OCR": 0.7,
            "FRESHNESS": 0.9,
        }


    def fuse(self, case_id: str) -> FusionResult:
        """Fuse all evidence atoms into a recommendation"""
        atoms = self.session.exec(
            select(EvidenceAtom).where(EvidenceAtom.case_id == case_id)
        ).all()

        if not atoms:
            return FusionResult(
                case_id=case_id,
                recommendation=RecommendationType.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                reasoning="No evidence available for fusion",
                recommended_action="Collect documents and biometrics",
                limitations=["No evidence atoms generated"],
            )

        contributions = []
        positive_score = 0.0
        negative_score = 0.0

        # Process each evidence atom
        for atom in atoms:
            contrib = self._compute_contribution(atom)
            contributions.append(contrib)

            if contrib.contribution > 0:
                positive_score += contrib.contribution
            else:
                negative_score += abs(contrib.contribution)

        net_score = positive_score - negative_score

        # Determine recommendation
        recommendation, confidence, reasoning = self._determine_recommendation(
            net_score, contributions, atoms
        )

        # Build evidence breakdown
        primary_reasons = self._extract_primary_reasons(contributions)
        supporting = [c for c in contributions if c.contribution <= 0 and c.severity in [EvidenceSeverity.INFO, EvidenceSeverity.LOW]]
        contradicting = [c for c in contributions if c.contribution > 0 and c.severity in [EvidenceSeverity.HIGH, EvidenceSeverity.CRITICAL]]

        # Build critical flags (from concern evidence atoms)
        critical_flags = list(set([
            c.evidence_type for c in contributions
            if c.contribution < 0 and c.severity in [EvidenceSeverity.HIGH, EvidenceSeverity.CRITICAL]
        ]))

        # Freshness breakdown dictionary
        freshness_breakdown = {
            "VERIFIED_FRESH": sum(1 for a in atoms if a.freshness == ModelFreshnessState.VERIFIED_FRESH),
            "VERIFIED_STALE": sum(1 for a in atoms if a.freshness == ModelFreshnessState.VERIFIED_STALE),
            "UNAVAILABLE": sum(1 for a in atoms if a.freshness == ModelFreshnessState.UNAVAILABLE),
            "CONFIRMED_ADVERSE": sum(1 for a in atoms if a.freshness == ModelFreshnessState.CONFIRMED_ADVERSE),
        }

        # Freshness warnings
        freshness_warnings = []
        stale_count = freshness_breakdown["VERIFIED_STALE"]
        unavailable_count = freshness_breakdown["UNAVAILABLE"]
        adverse_count = freshness_breakdown["CONFIRMED_ADVERSE"]

        if stale_count > 0:
            freshness_warnings.append(f"{stale_count} evidence items from stale data (> policy threshold)")
        if unavailable_count > 0:
            freshness_warnings.append(f"{unavailable_count} evidence items unavailable (offline or no cache)")
        if adverse_count > 0:
            freshness_warnings.append(f"{adverse_count} confirmed adverse records")

        # Limitations
        limitations = [
            "PROTOTYPE: Fusion weights are heuristic, not statistically calibrated",
            "Liveness detection is prototype-level, not certified",
            "Tamper detection limited to detectable artifacts",
            "No real government database integration (simulated)",
            "Thresholds require operational tuning",
        ]

        # Recommended action
        action_map = {
            RecommendationType.LOW_CONCERN: "Primary clearance recommended, subject to officer judgment",
            RecommendationType.SECONDARY_INSPECTION: "Manual/secondary verification recommended",
            RecommendationType.HIGH_CONCERN: "Enhanced inspection/escalation recommended",
            RecommendationType.INSUFFICIENT_EVIDENCE: "Authoritative verification/secondary inspection recommended",
        }

        return FusionResult(
            case_id=case_id,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            primary_reasons=primary_reasons,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            data_freshness_warnings=freshness_warnings,
            stale_evidence_count=stale_count,
            unavailable_evidence_count=unavailable_count,
            adverse_evidence_count=adverse_count,
            limitations=limitations,
            recommended_action=action_map.get(recommendation, "Officer review required"),
            evidence_atoms_considered=len(atoms),
            positive_score=positive_score,
            negative_score=negative_score,
            net_score=net_score,
            critical_flags=critical_flags,
            freshness_breakdown=freshness_breakdown,
        )

    def _compute_contribution(self, atom: EvidenceAtom) -> EvidenceContribution:
        """Compute weighted contribution of a single evidence atom"""

        # Base weight from severity
        base_weight = self.severity_weights.get(atom.severity, 0.5)

        # Confidence modifier
        confidence_mod = atom.confidence

        # Freshness modifier
        freshness_mod = self.freshness_modifiers.get(atom.freshness, 0.5)

        # Source reliability
        source_rel = self.source_reliability.get(atom.source.value, 0.7)

        # Combined weight
        weight = base_weight * confidence_mod * freshness_mod * source_rel

        # Determine direction (positive = reassurance, negative = concern)
        concern_types = {
            "DOB_MISMATCH", "NAME_MISMATCH", "DOCUMENT_NUMBER_MISMATCH",
            "MRZ_MISMATCH", "BARCODE_MISMATCH", "PHOTO_REPLACEMENT_SUSPECTED",
            "FACE_MISMATCH", "FACE_INCONCLUSIVE", "LIVENESS_INCONCLUSIVE",
            "LIVENESS_SPOOF_SUSPECTED", "DOCUMENT_EXPIRED", "VISA_INVALID",
            "WATCHLIST_STALE", "WATCHLIST_UNAVAILABLE", "WATCHLIST_ADVERSE",
            "WATCHLIST_HIT", "PASSPORT_REVOKED", "DOCUMENT_TAMPER_PHOTO",
            "CROSS_FIELD_CONFLICT_DOB", "IDENTITY_FRAGMENTATION", "OCR_UNCERTAIN",
            "TAMPER_SUSPECTED", "CROSS_FIELD_MISMATCH", "VALIDATION_FAILED",
            "TRAVEL_RULE_VIOLATION",
        }

        reassurance_types = {
            "FACE_MATCH", "LIVENESS_PASS", "MRZ_VALID", "WATCHLIST_CLEAN",
            "PASSPORT_VALID", "VISA_VALID", "DOCUMENT_VALID",
        }

        is_concern = atom.evidence_type in concern_types
        is_reassurance = atom.evidence_type in reassurance_types

        # Default: if severity is HIGH/CRITICAL, it's concern; if INFO/LOW, it's reassurance
        if not is_concern and not is_reassurance:
            is_concern = atom.severity in [ModelEvidenceSeverity.HIGH, ModelEvidenceSeverity.CRITICAL]
            is_reassurance = atom.severity in [ModelEvidenceSeverity.INFO, ModelEvidenceSeverity.LOW]

        contribution = -weight if is_concern else weight

        return EvidenceContribution(
            evidence_id=atom.id,
            evidence_type=atom.evidence_type,
            source=atom.source.value,
            severity=atom.severity,
            confidence=atom.confidence,
            description=atom.description,
            explanation=atom.explanation,
            entities=ast.literal_eval(atom.entities) if atom.entities else [],
            freshness=atom.freshness,
            weight=weight,
            contribution=contribution,
        )

    def _determine_recommendation(
        self,
        net_score: float,
        contributions: List[EvidenceContribution],
        atoms: List[EvidenceAtom],
    ) -> tuple:
        """Determine recommendation from fused score"""

        # Count critical/high concerns (negative contribution)
        critical_count = sum(1 for c in contributions if c.severity == EvidenceSeverity.CRITICAL and c.contribution < 0)
        high_count = sum(1 for c in contributions if c.severity == EvidenceSeverity.HIGH and c.contribution < 0)

        # Check for adverse evidence
        has_adverse = any(a.freshness == ModelFreshnessState.CONFIRMED_ADVERSE for a in atoms)

        # Check for face mismatch
        has_face_mismatch = any(
            c.evidence_type == "FACE_MISMATCH" and c.contribution < 0
            for c in contributions
        )

        # Check for tamper evidence
        has_tamper = any(
            c.evidence_type in ["DOCUMENT_TAMPER_PHOTO", "TAMPER_SUSPECTED"] and c.contribution < 0
            for c in contributions
        )

        # Check for identity fragmentation
        has_fragmentation = any(
            c.evidence_type in ["IDENTITY_FRAGMENTATION", "CROSS_FIELD_CONFLICT_DOB"] and c.contribution < 0
            for c in contributions
        )

        # Decision logic
        if has_adverse or has_face_mismatch or has_tamper or critical_count > 0:
            recommendation = RecommendationType.HIGH_CONCERN
            if has_adverse and sum(1 for a in atoms if a.freshness == ModelFreshnessState.CONFIRMED_ADVERSE) >= 2:
                confidence = 0.95
            elif has_adverse:
                confidence = 0.95 if any(c.evidence_type == "WATCHLIST_HIT" for c in contributions) else 0.90
            else:
                confidence = 0.90
            reasoning = "Critical concern(s) detected: " + ", ".join([
                "Adverse watchlist/revocation record" if has_adverse else "",
                "Face mismatch with document" if has_face_mismatch else "",
                "Document tampering detected" if has_tamper else "",
                f"{critical_count} critical rule violation(s)" if critical_count > 0 else "",
            ]).strip(", ")

        elif has_fragmentation or high_count >= 1 or net_score < 0.5:
            recommendation = RecommendationType.SECONDARY_INSPECTION
            confidence = 0.75
            reasoning = f"Elevated concern: identity fragmentation or {high_count} high-severity issue(s), net score {net_score:.2f}"

        else:
            recommendation = RecommendationType.LOW_CONCERN
            confidence = 0.85
            reasoning = f"Low concern: net score {net_score:.2f}, reassuring evidence"

        # Override for insufficient evidence (e.g. offline mode)
        total_atoms = len(atoms)
        unavail_atoms = sum(1 for a in atoms if a.freshness == ModelFreshnessState.UNAVAILABLE)

        if unavail_atoms >= 3 or total_atoms < 3:
            recommendation = RecommendationType.INSUFFICIENT_EVIDENCE
            confidence = 0.4
            reasoning = f"Insufficient evidence: {unavail_atoms} status checks unavailable"

        return recommendation, confidence, reasoning


    def _extract_primary_reasons(self, contributions: List[EvidenceContribution]) -> List[str]:
        """Extract primary reasons for the recommendation"""
        # Top contributing concerns
        concerns = [c for c in contributions if c.contribution > 0]
        concerns.sort(key=lambda x: x.contribution, reverse=True)

        reasons = []
        for c in concerns[:5]:  # Top 5
            reasons.append(f"{c.evidence_type}: {c.description}")

        return reasons


def generate_recommendation(case_id: str, session: Session) -> FusionResult:
    """Convenience function"""
    engine = EvidenceFusionEngine(session)
    return engine.fuse(case_id)


def _calculate_fusion_score(atoms: List[EvidenceAtom], session=None) -> tuple:
    """Calculate fusion score from evidence atoms (standalone for testing)"""
    # Create a minimal engine instance just for scoring
    # If no session provided, use a mock-like session that just works for _compute_contribution
    if session is None:
        from unittest.mock import Mock
        session = Mock()

    engine = EvidenceFusionEngine(session)

    positive_score = 0.0
    negative_score = 0.0

    for atom in atoms:
        contrib = engine._compute_contribution(atom)
        if contrib.contribution > 0:
            positive_score += contrib.contribution
        else:
            negative_score += abs(contrib.contribution)

    net_score = positive_score - negative_score
    confidence = min(0.99, (positive_score + negative_score) / max(1, len(atoms)) * 0.5 + 0.5)

    return positive_score, negative_score, net_score, confidence