# BIIP-SIH2026 Evidence Atom Generator
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select

from app.models.evidence import EvidenceAtom, EvidenceSeverity, EvidenceSource, FreshnessState
from app.models.case import Case
from app.models.document import Document
from app.models.document_field import DocumentField
from app.models.face_result import FaceResult, FaceMatchResult, LivenessResult
from app.models.tamper_result import TamperResult
from app.models.identity_graph import IdentityNode, IdentityEdge
from app.services.identity_graph.models import Conflict, ConflictSeverity


class EvidenceAtomGenerator:
    """Generate structured evidence atoms from all subsystems"""

    def __init__(self, session: Session):
        self.session = session

    def generate_all(self, case_id: str) -> List[EvidenceAtom]:
        """Generate all evidence atoms for a case"""
        atoms = []

        # Clear existing atoms for this case
        existing = self.session.exec(
            select(EvidenceAtom).where(EvidenceAtom.case_id == case_id)
        ).all()
        for a in existing:
            self.session.delete(a)

        # 1. OCR/Extraction evidence
        atoms.extend(self._generate_ocr_evidence(case_id))

        # 2. MRZ evidence
        atoms.extend(self._generate_mrz_evidence(case_id))

        # 3. Barcode evidence
        atoms.extend(self._generate_barcode_evidence(case_id))

        # 4. Document validation evidence
        atoms.extend(self._generate_validation_evidence(case_id))

        # 5. Tamper evidence
        atoms.extend(self._generate_tamper_evidence(case_id))

        # 6. Face verification evidence
        atoms.extend(self._generate_face_evidence(case_id))

        # 7. Liveness evidence
        atoms.extend(self._generate_liveness_evidence(case_id))

        # 8. Identity graph conflicts
        atoms.extend(self._generate_graph_evidence(case_id))

        # 9. Status/freshness evidence
        atoms.extend(self._generate_status_evidence(case_id))

        # Persist all
        for atom in atoms:
            self.session.add(atom)
        self.session.commit()

        return atoms

    def _generate_ocr_evidence(self, case_id: str) -> List[EvidenceAtom]:
        """Generate evidence from OCR extraction"""
        atoms = []

        documents = self.session.exec(
            select(Document).where(Document.case_id == case_id)
        ).all()

        for doc in documents:
            fields = self.session.exec(
                select(DocumentField).where(
                    DocumentField.document_id == doc.id,
                    DocumentField.source == "OCR"
                )
            ).all()

            low_conf_fields = [f for f in fields if f.confidence < 0.7]
            if low_conf_fields:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="OCR_UNCERTAIN",
                    source=EvidenceSource.OCR,
                    severity=EvidenceSeverity.MEDIUM,
                    confidence=0.8,
                    description=f"{len(low_conf_fields)} OCR fields with low confidence",
                    explanation=f"Fields: {', '.join([f.field_name for f in low_conf_fields])}",
                    entities=json.dumps([f"doc_{doc.id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="paddleocr-2.7.3",
                ))

        return atoms

    def _generate_mrz_evidence(self, case_id: str) -> List[EvidenceAtom]:
        """Generate evidence from MRZ validation"""
        atoms = []

        documents = self.session.exec(
            select(Document).where(Document.case_id == case_id)
        ).all()

        for doc in documents:
            if doc.mrz_raw:
                if doc.mrz_valid:
                    atoms.append(EvidenceAtom(
                        case_id=case_id,
                        evidence_type="MRZ_VALID",
                        source=EvidenceSource.MRZ,
                        severity=EvidenceSeverity.INFO,
                        confidence=0.95,
                        description="MRZ check digits valid",
                        entities=json.dumps([f"doc_{doc.id}"]),
                        freshness=FreshnessState.VERIFIED_FRESH,
                        rule_or_model_version="mrz-parser-0.1",
                    ))
                else:
                    atoms.append(EvidenceAtom(
                        case_id=case_id,
                        evidence_type="MRZ_INVALID",
                        source=EvidenceSource.MRZ,
                        severity=EvidenceSeverity.HIGH,
                        confidence=0.9,
                        description="MRZ check digits invalid",
                        explanation="One or more MRZ check digits failed validation",
                        entities=json.dumps([f"doc_{doc.id}"]),
                        freshness=FreshnessState.VERIFIED_FRESH,
                        rule_or_model_version="mrz-parser-0.1",
                    ))

        return atoms

    def _generate_barcode_evidence(self, case_id: str) -> List[EvidenceAtom]:
        """Generate evidence from barcode/QR"""
        atoms = []

        documents = self.session.exec(
            select(Document).where(Document.case_id == case_id)
        ).all()

        for doc in documents:
            fields = self.session.exec(
                select(DocumentField).where(
                    DocumentField.document_id == doc.id,
                    DocumentField.source == "BARCODE"
                )
            ).all()

            for field in fields:
                # Check if barcode field matches OCR/MRZ
                matched = self.session.exec(
                    select(DocumentField).where(DocumentField.id == field.matched_field_id)
                ).first()

                if matched and field.value and matched.value:
                    if self._normalize(field.value) != self._normalize(matched.value):
                        atoms.append(EvidenceAtom(
                            case_id=case_id,
                            evidence_type="BARCODE_MISMATCH",
                            source=EvidenceSource.BARCODE,
                            severity=EvidenceSeverity.HIGH,
                            confidence=0.85,
                            description=f"Barcode {field.field_name} differs from {matched.source}",
                            explanation=f"Barcode: '{field.value}' vs {matched.source}: '{matched.value}'",
                            entities=json.dumps([f"doc_{doc.id}"]),
                            freshness=FreshnessState.VERIFIED_FRESH,
                            rule_or_model_version="pyzbar-0.1.9",
                        ))

        return atoms

    def _generate_validation_evidence(self, case_id: str) -> List[EvidenceAtom]:
        """Generate evidence from document validation"""
        atoms = []

        documents = self.session.exec(
            select(Document).where(Document.case_id == case_id)
        ).all()

        for doc in documents:
            fields = self.session.exec(
                select(DocumentField).where(DocumentField.document_id == doc.id)
            ).all()

            invalid_fields = [f for f in fields if f.is_valid is False]
            if invalid_fields:
                for field in invalid_fields:
                    is_expiry = "expiry" in field.field_name or "expired" in (field.validation_error or "").lower()
                    severity = EvidenceSeverity.CRITICAL if is_expiry else EvidenceSeverity.HIGH
                    evidence_type = "DOCUMENT_EXPIRED" if is_expiry else "VALIDATION_FAILED"

                    atoms.append(EvidenceAtom(
                        case_id=case_id,
                        evidence_type=evidence_type,
                        source=EvidenceSource.DOCUMENT_VALIDATION,
                        severity=severity,
                        confidence=0.95,
                        description=f"Validation failed: {field.field_name}",
                        explanation=field.validation_error or "Validation failed",
                        entities=json.dumps([f"doc_{doc.id}"]),
                        freshness=FreshnessState.VERIFIED_FRESH,
                        rule_or_model_version="rule-engine-1.0",
                    ))
            elif fields:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="DOCUMENT_VALID",
                    source=EvidenceSource.DOCUMENT_VALIDATION,
                    severity=EvidenceSeverity.INFO,
                    confidence=0.9,
                    description=f"{doc.document_type.value} document fields valid",
                    explanation="All document field validation rules passed",
                    entities=json.dumps([f"doc_{doc.id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="rule-engine-1.0",
                ))

        return atoms


    def _generate_tamper_evidence(self, case_id: str) -> List[EvidenceAtom]:
        """Generate evidence from tamper detection"""
        atoms = []

        tamper_results = self.session.exec(
            select(TamperResult).where(TamperResult.case_id == case_id)
        ).all()

        for tr in tamper_results:
            if tr.tampered:
                reasons_list = []
                if tr.reasons:
                    if isinstance(tr.reasons, list):
                        reasons_list = tr.reasons
                    elif isinstance(tr.reasons, str):
                        try:
                            import json
                            reasons_list = json.loads(tr.reasons)
                        except Exception:
                            reasons_list = [tr.reasons]

                exp_str = "; ".join(reasons_list) if reasons_list else "Multiple layers indicate possible manipulation"

                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="DOCUMENT_TAMPER_PHOTO",
                    source=EvidenceSource.TAMPER_ANALYSIS,
                    severity=EvidenceSeverity.CRITICAL,
                    confidence=tr.confidence or 0.85,
                    description="Photo substitution detected",
                    explanation=exp_str,
                    entities=json.dumps([f"doc_{tr.document_id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="tamper-detector-1.0",
                ))

                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="TAMPER_SUSPECTED",
                    source=EvidenceSource.TAMPER_ANALYSIS,
                    severity=EvidenceSeverity.HIGH,
                    confidence=tr.confidence or 0.85,
                    description="Document tampering suspected",
                    explanation=exp_str,
                    entities=json.dumps([f"doc_{tr.document_id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="tamper-detector-1.0",
                ))

                if tr.cross_field_consistency:
                    import json
                    try:
                        data = json.loads(tr.cross_field_consistency)
                        if data.get("mismatches", 0) > 0:
                            atoms.append(EvidenceAtom(
                                case_id=case_id,
                                evidence_type="CROSS_FIELD_MISMATCH",
                                source=EvidenceSource.TAMPER_ANALYSIS,
                                severity=EvidenceSeverity.HIGH,
                                confidence=0.85,
                                description=f"Cross-field mismatches: {data['mismatches']}",
                                entities=json.dumps([f"doc_{tr.document_id}"]),
                                freshness=FreshnessState.VERIFIED_FRESH,
                                rule_or_model_version="tamper-detector-1.0",
                            ))
                    except Exception:
                        pass

        return atoms

    def _generate_face_evidence(self, case_id: str) -> List[EvidenceAtom]:
        """Generate evidence from face verification"""
        atoms = []

        face_results = self.session.exec(
            select(FaceResult).where(
                FaceResult.case_id == case_id,
                FaceResult.source_type == "LIVE_CAPTURE"
            )
        ).all()

        for fr in face_results:
            if fr.match_result == FaceMatchResult.MATCH:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="FACE_MATCH",
                    source=EvidenceSource.FACE_VERIFICATION,
                    severity=EvidenceSeverity.INFO,
                    confidence=fr.match_score or 0.8,
                    description=f"Face matches document (similarity: {fr.match_score:.2f})",
                    entities=json.dumps([f"face_{fr.id}", f"doc_{fr.compared_to_document_id}"] if fr.compared_to_document_id else [f"face_{fr.id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="insightface-buffalo_l",
                ))
            elif fr.match_result == FaceMatchResult.MISMATCH:
                mismatch_confidence = 0.95
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="FACE_MISMATCH",
                    source=EvidenceSource.FACE_VERIFICATION,
                    severity=EvidenceSeverity.CRITICAL,
                    confidence=mismatch_confidence,
                    description=f"Face does not match document (similarity: {fr.match_score:.2f})",
                    explanation="Live face embedding significantly differs from document photo embedding",
                    entities=json.dumps([f"face_{fr.id}", f"doc_{fr.compared_to_document_id}"] if fr.compared_to_document_id else [f"face_{fr.id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="insightface-buffalo_l",
                ))

            elif fr.match_result == FaceMatchResult.INCONCLUSIVE:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="FACE_INCONCLUSIVE",
                    source=EvidenceSource.FACE_VERIFICATION,
                    severity=EvidenceSeverity.MEDIUM,
                    confidence=0.5,
                    description="Face verification inconclusive",
                    explanation=f"Similarity score ({fr.match_score:.2f}) near threshold or poor quality",
                    entities=json.dumps([f"face_{fr.id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="insightface-buffalo_l",
                ))

            # Quality-based evidence
            if fr.quality_score < 0.5:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="FACE_QUALITY_LOW",
                    source=EvidenceSource.FACE_VERIFICATION,
                    severity=EvidenceSeverity.MEDIUM,
                    confidence=0.8,
                    description=f"Face capture quality low (score: {fr.quality_score:.2f})",
                    explanation="Poor quality may affect verification reliability",
                    entities=json.dumps([f"face_{fr.id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="face-quality-1.0",
                ))

        return atoms

    def _generate_liveness_evidence(self, case_id: str) -> List[EvidenceAtom]:
        """Generate evidence from liveness check"""
        atoms = []

        face_results = self.session.exec(
            select(FaceResult).where(
                FaceResult.case_id == case_id,
                FaceResult.source_type == "LIVE_CAPTURE"
            )
        ).all()

        for fr in face_results:
            if fr.liveness_result == LivenessResult.LIVE:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="LIVENESS_PASS",
                    source=EvidenceSource.LIVENESS,
                    severity=EvidenceSeverity.INFO,
                    confidence=fr.liveness_confidence,
                    description="Liveness check passed",
                    entities=json.dumps([f"face_{fr.id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="liveness-prototype-1.0",
                ))
            elif fr.liveness_result == LivenessResult.SPOOF_SUSPECTED:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="LIVENESS_SPOOF_SUSPECTED",
                    source=EvidenceSource.LIVENESS,
                    severity=EvidenceSeverity.HIGH,
                    confidence=fr.liveness_confidence,
                    description="Presentation attack suspected",
                    explanation="Liveness indicators suggest possible spoof (photo, screen, mask)",
                    entities=json.dumps([f"face_{fr.id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="liveness-prototype-1.0",
                ))
            elif fr.liveness_result == LivenessResult.INCONCLUSIVE:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="LIVENESS_INCONCLUSIVE",
                    source=EvidenceSource.LIVENESS,
                    severity=EvidenceSeverity.MEDIUM,
                    confidence=0.5,
                    description="Liveness check inconclusive",
                    explanation="Insufficient evidence to determine liveness",
                    entities=json.dumps([f"face_{fr.id}"]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    rule_or_model_version="liveness-prototype-1.0",
                ))

        return atoms

    def _generate_graph_evidence(self, case_id: str) -> List[EvidenceAtom]:
        """Generate evidence from identity graph conflicts"""
        atoms = []

        # Get conflicts from identity graph
        conflicts = self.session.exec(
            select(IdentityEdge).where(
                IdentityEdge.case_id == case_id,
                IdentityEdge.edge_type == "CONFLICTS_WITH"
            )
        ).all()

        for edge in conflicts:
            import json
            props = {}
            if edge.properties:
                if isinstance(edge.properties, dict):
                    props = edge.properties
                elif isinstance(edge.properties, str):
                    try:
                        props = json.loads(edge.properties)
                    except Exception:
                        try:
                            import ast
                            props = ast.literal_eval(edge.properties)
                        except Exception:
                            props = {}

            c_type = props.get("conflict_type")
            if not c_type:
                field_name = props.get("field", "FIELD").upper()
                c_type = "CROSS_FIELD_CONFLICT_DOB" if field_name in ["BIRTH_DATE", "DATE_OF_BIRTH", "DOB"] else f"{field_name}_MISMATCH"

            atoms.append(EvidenceAtom(
                case_id=case_id,
                evidence_type=c_type,
                source=EvidenceSource.IDENTITY_GRAPH,
                severity=EvidenceSeverity.HIGH,
                confidence=edge.weight or 0.9,
                description=f"Cross-document conflict: {props.get('field', 'field')}",
                explanation=props.get("description", f"Conflict detected on field {props.get('field', 'field')}"),
                entities=json.dumps([edge.source_node_id, edge.target_node_id]),
                freshness=FreshnessState.VERIFIED_FRESH,
                rule_or_model_version="identity-graph-1.0",
            ))

        if conflicts:
            atoms.append(EvidenceAtom(
                case_id=case_id,
                evidence_type="IDENTITY_FRAGMENTATION",
                source=EvidenceSource.IDENTITY_GRAPH,
                severity=EvidenceSeverity.HIGH,
                confidence=0.9,
                description="Identity fragmentation detected across document clusters",
                explanation="Conflicting identity attributes detected across documents",
                entities=json.dumps([c.id for c in conflicts]),
                freshness=FreshnessState.VERIFIED_FRESH,
                rule_or_model_version="identity-graph-1.0",
            ))

        return atoms

    def _generate_status_evidence(self, case_id: str) -> List[EvidenceAtom]:
        """Generate evidence from status checks"""
        atoms = []

        from app.models.status_cache import StatusCache, FreshnessState as CacheFreshnessState, StatusType

        status_records = self.session.exec(
            select(StatusCache).where(StatusCache.case_id == case_id)
        ).all()

        for record in status_records:
            if record.freshness == CacheFreshnessState.VERIFIED_STALE:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="WATCHLIST_STALE",
                    source=EvidenceSource.FRESHNESS,
                    severity=EvidenceSeverity.MEDIUM,
                    confidence=0.9,
                    description=f"{record.status_type.value} status is stale",
                    explanation=f"Last synchronized {record.last_synced_at}, policy allows {record.freshness_policy_hours}h",
                    entities=json.dumps([record.entity_identifier]),
                    freshness=FreshnessState.VERIFIED_STALE,
                    last_synced_at=record.last_synced_at,
                    freshness_policy_hours=record.freshness_policy_hours,
                    rule_or_model_version="freshness-engine-1.0",
                ))
            elif record.freshness == CacheFreshnessState.UNAVAILABLE:
                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type="WATCHLIST_UNAVAILABLE",
                    source=EvidenceSource.FRESHNESS,
                    severity=EvidenceSeverity.MEDIUM,
                    confidence=0.9,
                    description=f"{record.status_type.value} status unavailable",
                    explanation="No cached data and central service unreachable",
                    entities=json.dumps([record.entity_identifier]),
                    freshness=FreshnessState.UNAVAILABLE,
                    last_synced_at=record.last_synced_at,
                    freshness_policy_hours=record.freshness_policy_hours,
                    rule_or_model_version="freshness-engine-1.0",
                ))
            elif record.freshness == CacheFreshnessState.CONFIRMED_ADVERSE:
                if record.status == "WATCHLISTED" or record.status_type == StatusType.WATCHLIST:
                    ev_type = "WATCHLIST_HIT"
                elif record.status == "REVOKED" or record.status_type == StatusType.PASSPORT:
                    ev_type = "PASSPORT_REVOKED"
                else:
                    ev_type = "WATCHLIST_ADVERSE"

                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type=ev_type,
                    source=EvidenceSource.WATCHLIST,
                    severity=EvidenceSeverity.CRITICAL,
                    confidence=0.99,
                    description=f"Adverse status: {record.status}",
                    explanation=record.adverse_reason or "Recorded in watchlist/revocation database",
                    entities=json.dumps([record.entity_identifier]),
                    freshness=FreshnessState.CONFIRMED_ADVERSE,
                    last_synced_at=record.last_synced_at,
                    freshness_policy_hours=record.freshness_policy_hours,
                    rule_or_model_version="freshness-engine-1.0",
                ))
            elif record.freshness == CacheFreshnessState.VERIFIED_FRESH and record.status in ["CLEAN", "VALID"]:
                if record.status_type == StatusType.PASSPORT:
                    ev_type = "PASSPORT_VALID"
                elif record.status_type == StatusType.VISA:
                    ev_type = "VISA_VALID"
                else:
                    ev_type = "WATCHLIST_CLEAN"

                atoms.append(EvidenceAtom(
                    case_id=case_id,
                    evidence_type=ev_type,
                    source=EvidenceSource.WATCHLIST if record.status_type == StatusType.WATCHLIST else EvidenceSource.DOCUMENT_VALIDATION,
                    severity=EvidenceSeverity.INFO,
                    confidence=0.9,
                    description=f"{record.status_type.value} status: {record.status}",
                    explanation="No adverse records found in authoritative database",
                    entities=json.dumps([record.entity_identifier]),
                    freshness=FreshnessState.VERIFIED_FRESH,
                    last_synced_at=record.last_synced_at,
                    freshness_policy_hours=record.freshness_policy_hours,
                    rule_or_model_version="freshness-engine-1.0",
                ))

        return atoms


    def _normalize(self, value: str) -> str:
        """Normalize for comparison"""
        import re
        normalized = re.sub(r"\s+", " ", value.strip().upper())
        normalized = normalized.replace("Ø", "O").replace("Å", "A").replace("Ä", "AE")
        normalized = normalized.replace("Ö", "OE").replace("Ü", "UE").replace("ß", "SS")
        return normalized


def generate_evidence_atoms(case_id: str, session: Session) -> List[EvidenceAtom]:
    """Convenience function"""
    generator = EvidenceAtomGenerator(session)
    return generator.generate_all(case_id)