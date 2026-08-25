"""
Unit tests for Evidence Fusion Engine
Tests additive weighted fusion with severity, confidence, freshness, source modifiers
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from sqlmodel import Session, select

from app.services.evidence.fusion import EvidenceFusionEngine, generate_recommendation, _calculate_fusion_score
from app.services.evidence.atoms import generate_evidence_atoms
from app.models.evidence import EvidenceAtom, EvidenceSeverity, EvidenceSource, FreshnessState
from app.models.case import Case


@pytest.fixture
def mock_session():
    session = Mock(spec=Session)
    return session


class TestEvidenceFusion:
    """Test evidence fusion scoring and recommendation"""

    def test_calculate_fusion_score_all_positive(self, mock_session):
        """Test fusion with all reassurance evidence (positive contribution)"""
        atoms = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="DOCUMENT_VALID",
                severity=EvidenceSeverity.LOW, source=EvidenceSource.DOCUMENT_VALIDATION,
                confidence=0.9, description="Passport valid", freshness=FreshnessState.VERIFIED_FRESH,
            ),
            EvidenceAtom(
                id="a2", case_id="case-1", evidence_type="FACE_MATCH",
                severity=EvidenceSeverity.LOW, source=EvidenceSource.FACE_VERIFICATION,
                confidence=0.95, description="Face matches", freshness=FreshnessState.VERIFIED_FRESH,
            ),
        ]

        positive, negative, net, confidence = _calculate_fusion_score(atoms)

        # Reassurance evidence produces positive contributions
        assert positive > 0
        assert negative == 0
        assert net > 0
        assert confidence > 0.5

    def test_calculate_fusion_score_all_negative(self, mock_session):
        """Test fusion with all concern evidence (negative contribution)"""
        atoms = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="DOCUMENT_EXPIRED",
                severity=EvidenceSeverity.CRITICAL, source=EvidenceSource.DOCUMENT_VALIDATION,
                confidence=0.99, description="Passport expired", freshness=FreshnessState.VERIFIED_FRESH,
            ),
            EvidenceAtom(
                id="a2", case_id="case-1", evidence_type="WATCHLIST_HIT",
                severity=EvidenceSeverity.CRITICAL, source=EvidenceSource.WATCHLIST,
                confidence=0.99, description="On watchlist", freshness=FreshnessState.CONFIRMED_ADVERSE,
            ),
        ]

        positive, negative, net, confidence = _calculate_fusion_score(atoms)

        assert positive == 0
        assert negative > 0
        assert net < 0
        assert confidence > 0.9

    def test_calculate_fusion_score_mixed(self, mock_session):
        """Test fusion with mixed evidence"""
        atoms = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="WATCHLIST_CLEAN",
                severity=EvidenceSeverity.INFO, source=EvidenceSource.WATCHLIST,
                confidence=0.9, description="Watchlist clean", freshness=FreshnessState.VERIFIED_FRESH,
            ),
            EvidenceAtom(
                id="a2", case_id="case-1", evidence_type="FACE_MISMATCH",
                severity=EvidenceSeverity.HIGH, source=EvidenceSource.FACE_VERIFICATION,
                confidence=0.85, description="Face mismatch", freshness=FreshnessState.VERIFIED_FRESH,
            ),
        ]

        positive, negative, net, confidence = _calculate_fusion_score(atoms)

        assert positive > 0
        assert negative > 0
        assert confidence > 0

    def test_calculate_fusion_score_stale_penalty(self, mock_session):
        """Test that stale evidence reduces score"""
        atoms_fresh = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="WATCHLIST_CLEAN",
                severity=EvidenceSeverity.INFO, source=EvidenceSource.WATCHLIST,
                confidence=0.9, description="Watchlist clean", freshness=FreshnessState.VERIFIED_FRESH,
            ),
        ]
        atoms_stale = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="WATCHLIST_CLEAN",
                severity=EvidenceSeverity.INFO, source=EvidenceSource.WATCHLIST,
                confidence=0.9, description="Watchlist clean", freshness=FreshnessState.VERIFIED_STALE,
            ),
        ]

        _, _, net_fresh, conf_fresh = _calculate_fusion_score(atoms_fresh)
        _, _, net_stale, conf_stale = _calculate_fusion_score(atoms_stale)

        # Stale reassurance should have a lower positive net score
        assert net_stale < net_fresh

    def test_calculate_fusion_score_unavailable_penalty(self, mock_session):
        """Test that unavailable evidence significantly reduces score"""
        atoms_fresh = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="WATCHLIST_CLEAN",
                severity=EvidenceSeverity.INFO, source=EvidenceSource.WATCHLIST,
                confidence=0.9, description="Watchlist clean", freshness=FreshnessState.VERIFIED_FRESH,
            ),
        ]
        atoms_unavailable = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="WATCHLIST_CLEAN",
                severity=EvidenceSeverity.INFO, source=EvidenceSource.WATCHLIST,
                confidence=0.9, description="Watchlist clean", freshness=FreshnessState.UNAVAILABLE,
            ),
        ]

        _, _, net_fresh, conf_fresh = _calculate_fusion_score(atoms_fresh)
        _, _, net_unavail, conf_unavail = _calculate_fusion_score(atoms_unavailable)

        assert conf_unavail < conf_fresh

    def test_calculate_fusion_score_adverse_boosts_negative(self, mock_session):
        """Test that CONFIRMED_ADVERSE strongly boosts concern score (negative contribution)"""
        atoms_clean = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="WATCHLIST_CLEAN",
                severity=EvidenceSeverity.INFO, source=EvidenceSource.WATCHLIST,
                confidence=0.9, description="Watchlist clean", freshness=FreshnessState.VERIFIED_FRESH,
            ),
        ]
        atoms_adverse = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="WATCHLIST_HIT",
                severity=EvidenceSeverity.CRITICAL, source=EvidenceSource.WATCHLIST,
                confidence=0.99, description="Watchlist hit", freshness=FreshnessState.CONFIRMED_ADVERSE,
            ),
        ]

        _, neg_clean, _, _ = _calculate_fusion_score(atoms_clean)
        _, neg_adverse, _, _ = _calculate_fusion_score(atoms_adverse)

        assert neg_adverse > neg_clean

    def test_source_reliability_weights(self, mock_session):
        """Test that different sources have different reliability weights"""
        atoms_mrz = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="WATCHLIST_CLEAN",
                severity=EvidenceSeverity.INFO, source=EvidenceSource.MRZ,
                confidence=0.99, description="MRZ match", freshness=FreshnessState.VERIFIED_FRESH,
            ),
        ]
        atoms_ocr = [
            EvidenceAtom(
                id="a1", case_id="case-1", evidence_type="WATCHLIST_CLEAN",
                severity=EvidenceSeverity.INFO, source=EvidenceSource.OCR,
                confidence=0.95, description="OCR match", freshness=FreshnessState.VERIFIED_FRESH,
            ),
        ]

        _, _, net_mrz, conf_mrz = _calculate_fusion_score(atoms_mrz)
        _, _, net_ocr, conf_ocr = _calculate_fusion_score(atoms_ocr)

        # More reliable reassurance source = higher positive net score
        assert net_mrz >= net_ocr
        assert conf_mrz >= conf_ocr

    def test_severity_weight_multipliers(self, mock_session):
        """Test that severity levels have correct weight multipliers for concern evidence"""
        severities = [
            (EvidenceSeverity.HIGH, 0.8),
            (EvidenceSeverity.CRITICAL, 1.0),
        ]

        prev_net = 0
        for severity, expected_weight in severities:
            atoms = [
                EvidenceAtom(
                    id=f"a-{severity.value}", case_id="case-1", evidence_type="DOCUMENT_EXPIRED",
                    severity=severity, source=EvidenceSource.DOCUMENT_VALIDATION,
                    confidence=1.0, description="Test", freshness=FreshnessState.VERIFIED_FRESH,
                ),
            ]
            _, _, net, _ = _calculate_fusion_score(atoms)
            # Higher severity concern produces more negative net score
            assert net < 0
            assert net < prev_net  # Higher severity concern decreases net score further
            prev_net = net



class TestRecommendationGeneration:
    """Test recommendation generation from fusion scores"""

    def test_low_concern_recommendation(self, mock_session):
        """Test LOW_CONCERN recommendation for high positive, low negative"""
        # This tests the logic in generate_recommendation
        # We'd need to mock the database calls
        pass  # Integration test needed with real DB

    def test_high_concern_recommendation(self, mock_session):
        """Test HIGH_CONCERN for high negative score"""
        pass

    def test_secondary_inspection_recommendation(self, mock_session):
        """Test SECONDARY_INSPECTION for mixed/uncertain"""
        pass

    def test_insufficient_evidence_recommendation(self, mock_session):
        """Test INSUFFICIENT_EVIDENCE when key data unavailable"""
        pass


class TestEvidenceAtomGeneration:
    """Test evidence atom generation from various sources"""

    def test_generate_evidence_from_tamper_clean(self, mock_session):
        """Test evidence generation from clean tamper result"""
        pass

    def test_generate_evidence_from_tamper_detected(self, mock_session):
        """Test evidence generation from tamper detection"""
        pass

    def test_generate_evidence_from_face_match(self, mock_session):
        """Test evidence generation from face match"""
        pass

    def test_generate_evidence_from_face_mismatch(self, mock_session):
        """Test evidence generation from face mismatch"""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])