# BIIP-SIH2026 Demo API Router
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
import uuid
from datetime import datetime, timedelta

from app.core.database import get_session
from app.models.case import Case, CaseStatus, CheckpointType
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.document_field import DocumentField
from app.models.face_result import FaceResult, FaceMatchResult, LivenessResult
from app.models.tamper_result import TamperResult
from app.models.status_cache import StatusCache, StatusType, FreshnessState as CacheFreshnessState
from app.models.evidence import EvidenceAtom, EvidenceSeverity, EvidenceSource, FreshnessState
from app.models.identity_graph import IdentityNode, IdentityEdge
from app.services.evidence.atoms import generate_evidence_atoms
from app.services.evidence.fusion import generate_recommendation
from app.services.identity_graph.builder import build_identity_graph
from app.services.freshness.engine import FreshnessEngine
from app.services.sync.processor import SyncProcessor

router = APIRouter(prefix="/demo", tags=["demo"])


# Scenario definitions
SCENARIOS = [
    {
        "id": "scenario_1",
        "name": "Clean Traveler",
        "description": "Valid passport, valid visa, face match, clean watchlist",
        "expected_recommendation": "LOW_CONCERN",
        "documents": ["passport", "visa"],
        "face_scenario": "match",
    },
    {
        "id": "scenario_2",
        "name": "Expired Passport",
        "description": "Passport expired 6 months ago, valid visa",
        "expected_recommendation": "HIGH_CONCERN",
        "documents": ["passport", "visa"],
        "face_scenario": "match",
    },
    {
        "id": "scenario_3",
        "name": "Face Mismatch",
        "description": "Valid documents but live face doesn't match passport photo",
        "expected_recommendation": "HIGH_CONCERN",
        "documents": ["passport", "visa"],
        "face_scenario": "mismatch",
    },
    {
        "id": "scenario_4",
        "name": "Watchlist Hit",
        "description": "Valid documents, face match, but passport on INTERPOL SLTD",
        "expected_recommendation": "HIGH_CONCERN",
        "documents": ["passport", "visa"],
        "face_scenario": "match",
    },
    {
        "id": "scenario_5",
        "name": "Document Tampering",
        "description": "Passport shows signs of photo substitution and data alteration",
        "expected_recommendation": "HIGH_CONCERN",
        "documents": ["passport"],
        "face_scenario": "mismatch",
    },

    {
        "id": "scenario_6",
        "name": "Identity Fragmentation",
        "description": "Passport and visa have conflicting DOB and name fields",
        "expected_recommendation": "SECONDARY_INSPECTION",
        "documents": ["passport", "visa"],
        "face_scenario": "match",
    },
    {
        "id": "scenario_7",
        "name": "Offline Mode",
        "description": "Valid documents but central databases unreachable (stale/unavailable)",
        "expected_recommendation": "INSUFFICIENT_EVIDENCE",
        "documents": ["passport", "visa"],
        "face_scenario": "match",
    },
]


@router.get("/scenarios")
async def get_scenarios():
    """Get available demo scenarios"""
    return SCENARIOS


@router.post("/scenarios/{scenario_id}/run")
async def run_scenario(scenario_id: str, session: Session = Depends(get_session)):
    """Run a demo scenario and create a case"""
    scenario = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Create case
    case = Case(
        id=str(uuid.uuid4()),
        case_number=f"DEMO-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        status=CaseStatus.PROCESSING,
        officer_id="DEMO_OFFICER_001",
        location="Indira Gandhi International Airport, Terminal 3",
        checkpoint_type=CheckpointType.AIRPORT,
        priority=3,
    )
    session.add(case)
    session.commit()
    session.refresh(case)

    # Create documents based on scenario
    await _create_demo_documents(case.id, scenario, session)

    # Create face capture
    await _create_demo_face(case.id, scenario, session)

    # Run processing pipeline
    await _run_processing_pipeline(case.id, scenario, session)

    return {"case_id": case.id, "case_number": case.case_number}


@router.post("/load-test-data")
async def load_test_data(session: Session = Depends(get_session)):
    """Load synthetic test data for all scenarios"""
    for scenario in SCENARIOS:
        try:
            await run_scenario(scenario["id"], session)
        except Exception as e:
            print(f"Error loading scenario {scenario['id']}: {e}")
    return {"message": "Test data loaded for all scenarios"}


async def _create_demo_documents(case_id: str, scenario: dict, session: Session):
    """Create demo documents for a scenario"""
    now = datetime.utcnow()

    if "passport" in scenario["documents"]:
        # Determine expiry based on scenario
        if scenario["id"] == "scenario_2":  # Expired passport
            expiry = now - timedelta(days=180)
        else:
            expiry = now + timedelta(days=365 * 5)

        # Determine document number based on scenario
        if scenario["id"] == "scenario_4":  # Watchlist hit
            doc_number = "P<IND1234567"  # In SIMULATED_WATCHLIST
        else:
            doc_number = f"P<IND{uuid.uuid4().hex[:7].upper()}"

        passport = Document(
            id=str(uuid.uuid4()),
            case_id=case_id,
            document_type=DocumentType.PASSPORT,
            document_subtype="ORDINARY",
            country_code="IND",
            document_number=doc_number,
            mrz_raw=f"P<IND{doc_number[5:]}<<DEMO<TRAVELER<<<<<<<<<<<<<<<<<<<<<<",
            mrz_valid=True,
            barcode_raw=None,
            filename=f"demo_passport_{doc_number}.jpg",
            file_path=f"/demo/passport_{doc_number}.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            status=DocumentStatus.PROCESSED,
        )
        session.add(passport)
        session.commit()
        session.refresh(passport)

        # Add passport fields
        passport_fields = [
            ("surname", "DEMO", "OCR", 0.95),
            ("given_names", "TRAVELER", "OCR", 0.95),
            ("document_number", doc_number, "OCR", 0.98),
            ("document_number", doc_number, "MRZ", 0.99),
            ("nationality", "IND", "OCR", 0.98),
            ("nationality", "IND", "MRZ", 0.99),
            ("birth_date", "1990-01-15" if scenario["id"] != "scenario_6" else "1990-01-15", "OCR", 0.95),
            ("birth_date", "1990-01-15" if scenario["id"] != "scenario_6" else "1990-01-15", "MRZ", 0.99),
            ("sex", "M", "OCR", 0.98),
            ("sex", "M", "MRZ", 0.99),
            ("issue_date", (expiry - timedelta(days=365*10)).strftime("%Y-%m-%d"), "OCR", 0.95),
            ("expiry_date", expiry.strftime("%Y-%m-%d"), "OCR", 0.95),
            ("expiry_date", expiry.strftime("%Y-%m-%d"), "MRZ", 0.99),
            ("issuing_authority", "GOVT OF INDIA", "OCR", 0.90),
        ]

        for field_name, value, source, confidence in passport_fields:
            field = DocumentField(
                id=str(uuid.uuid4()),
                document_id=passport.id,
                field_name=field_name,
                value=value,
                confidence=confidence,
                source=source,
            )
            session.add(field)

        # Cross-field match for MRZ
        if scenario["id"] != "scenario_6":
            for f in session.exec(
                select(DocumentField).where(
                    DocumentField.document_id == passport.id,
                    DocumentField.source == "MRZ",
                )
            ).all():
                ocr_field = session.exec(
                    select(DocumentField).where(
                        DocumentField.document_id == passport.id,
                        DocumentField.field_name == f.field_name,
                        DocumentField.source == "OCR",
                    )
                ).first()
                if ocr_field:
                    f.matched_field_id = ocr_field.id

    if "visa" in scenario["documents"]:
        visa = Document(
            id=str(uuid.uuid4()),
            case_id=case_id,
            document_type=DocumentType.VISA,
            document_subtype="TOURIST",
            country_code="IND",
            document_number=f"VISA_IND_2024_{uuid.uuid4().hex[:3].upper()}",
            mrz_raw=None,
            barcode_raw=f"VISA|IND|{scenario['id']}|TOURIST|SINGLE",
            filename=f"demo_visa_{scenario['id']}.jpg",
            file_path=f"/demo/visa_{scenario['id']}.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            status=DocumentStatus.PROCESSED,
        )
        session.add(visa)
        session.commit()
        session.refresh(visa)

        # Visa fields
        visa_fields = [
            ("visa_number", visa.document_number, "OCR", 0.95),
            ("visa_number", visa.document_number, "BARCODE", 0.99),
            ("issuing_country", "IND", "OCR", 0.95),
            ("issuing_country", "IND", "BARCODE", 0.99),
            ("visa_type", "TOURIST", "OCR", 0.90),
            ("visa_type", "TOURIST", "BARCODE", 0.99),
            ("entry_date", (now + timedelta(days=1)).strftime("%Y-%m-%d"), "OCR", 0.95),
            ("expiry_date", (now + timedelta(days=180)).strftime("%Y-%m-%d"), "OCR", 0.95),
            ("expiry_date", (now + timedelta(days=180)).strftime("%Y-%m-%d"), "BARCODE", 0.99),
            ("number_of_entries", "1", "OCR", 0.95),
            ("number_of_entries", "1", "BARCODE", 0.99),
        ]

        if scenario["id"] == "scenario_6":  # Identity fragmentation - different DOB
            visa_fields.append(("birth_date", "1991-01-15", "OCR", 0.95))
            visa_fields.append(("birth_date", "1991-01-15", "BARCODE", 0.99))
        else:
            visa_fields.append(("birth_date", "1990-01-15", "OCR", 0.95))
            visa_fields.append(("birth_date", "1990-01-15", "BARCODE", 0.99))

        for field_name, value, source, confidence in visa_fields:
            field = DocumentField(
                id=str(uuid.uuid4()),
                document_id=visa.id,
                field_name=field_name,
                value=value,
                confidence=confidence,
                source=source,
            )
            session.add(field)

        # Cross-field match
        for f in session.exec(
            select(DocumentField).where(
                DocumentField.document_id == visa.id,
                DocumentField.source == "BARCODE",
            )
        ).all():
            ocr_field = session.exec(
                select(DocumentField).where(
                    DocumentField.document_id == visa.id,
                    DocumentField.field_name == f.field_name,
                    DocumentField.source == "OCR",
                )
            ).first()
            if ocr_field:
                f.matched_field_id = ocr_field.id

    session.commit()


async def _create_demo_face(case_id: str, scenario: dict, session: Session):
    """Create demo face capture"""
    face = FaceResult(
        id=str(uuid.uuid4()),
        case_id=case_id,
        document_id=None,  # Will be set when compared
        source_type="LIVE_CAPTURE",
        source_image_path=f"/demo/faces/{scenario['id']}_live.jpg",
        embedding=None,  # Would be computed
        face_detected=True,
        detection_confidence=0.95,
        quality_score=0.85,
        match_score=0.92 if scenario["face_scenario"] == "match" else 0.35,
        match_result=FaceMatchResult.MATCH if scenario["face_scenario"] == "match" else FaceMatchResult.MISMATCH,
        compared_to_document_id=None,
        liveness_result=LivenessResult.LIVE,
        liveness_confidence=0.88,
        liveness_details='{"blink": true, "turn_left": true, "turn_right": true}',
    )
    session.add(face)
    session.commit()


async def _run_processing_pipeline(case_id: str, scenario: dict, session: Session):
    """Run the full processing pipeline for a case"""
    # 1. Document validation
    from app.services.document.validator import validate_document
    documents = session.exec(select(Document).where(Document.case_id == case_id)).all()
    for doc in documents:
        result = validate_document(doc.id, session)
        # Update document fields with validation results
        from app.models.document_field import DocumentField
        for field_name, field_result in result.field_results.items():
            field = session.exec(
                select(DocumentField).where(
                    DocumentField.document_id == doc.id,
                    DocumentField.field_name == field_name
                )
            ).first()
            if field:
                field.is_valid = field_result["valid"]
                if not field_result["valid"] and field_result["violations"]:
                    field.validation_error = field_result["violations"][0].get("message", "Validation failed")

    # 2. Tamper analysis
    for doc in documents:
        tamper = TamperResult(
            id=str(uuid.uuid4()),
            case_id=case_id,
            document_id=doc.id,
            tampered=(scenario["id"] == "scenario_5"),
            confidence=0.85 if scenario["id"] == "scenario_5" else 0.15,
            reasons='["Photo substitution suspected", "ELA anomalies detected"]' if scenario["id"] == "scenario_5" else '[]',
            cross_field_consistency='{"mismatches": 0}' if scenario["id"] != "scenario_6" else '{"mismatches": 2}',
            image_analysis='{"ela_score": 0.1}' if scenario["id"] != "scenario_5" else '{"ela_score": 0.8}',
            photo_consistency='{"score": 0.9}' if scenario["id"] != "scenario_5" else '{"score": 0.3}',
        )
        session.add(tamper)

    # 3. Build identity graph
    build_identity_graph(case_id, session)

    # 4. Add status cache entries based on scenario (BEFORE generating evidence)
    await _create_status_cache(case_id, scenario, session)

    # 5. Generate evidence atoms
    generate_evidence_atoms(case_id, session)

    # 6. Run fusion
    generate_recommendation(case_id, session)

    # 7. Update case status
    case = session.get(Case, case_id)
    if case:
        case.status = CaseStatus.AWAITING_REVIEW
        session.add(case)

    session.commit()


async def _create_status_cache(case_id: str, scenario: dict, session: Session):
    """Create status cache entries for demo"""
    from datetime import datetime, timedelta
    from app.models.status_cache import StatusCache, FreshnessState as CacheFreshnessState, StatusType
    now = datetime.utcnow()
    engine = FreshnessEngine(session)

    documents = session.exec(select(Document).where(Document.case_id == case_id)).all()
    passport = next((d for d in documents if d.document_type == DocumentType.PASSPORT), None)
    visa = next((d for d in documents if d.document_type == DocumentType.VISA), None)

    # Offline mode - all central status checks unavailable
    if scenario["id"] == "scenario_7":
        for st_type, entity_id, src in [
            (StatusType.WATCHLIST, passport.document_number if passport else "P<IND44444444", "INTERPOL_SLTD"),
            (StatusType.VISA, visa.document_number if visa else "VISA_IND_2024_OFF", "VISA_SYSTEM"),
            (StatusType.PASSPORT, passport.document_number if passport else "P<IND44444444", "PASSPORT_REGISTRY"),
        ]:
            unavail_record = StatusCache(
                case_id=case_id,
                status_type=st_type,
                entity_identifier=entity_id,
                status="UNKNOWN",
                freshness=CacheFreshnessState.UNAVAILABLE,
                last_synced_at=now - timedelta(hours=48),
                freshness_policy_hours=6,
                source=src,
                is_adverse=False,
            )
            session.add(unavail_record)
        session.commit()
        return


    # Watchlist check
    if scenario["id"] == "scenario_4":
        engine.simulate_status_check(
            case_id=case_id,
            status_type=StatusType.WATCHLIST,
            entity_identifier=passport.document_number if passport else "UNKNOWN",
            source="INTERPOL_SLTD",
            status="WATCHLISTED",
            adverse_reason="Suspected document fraud ring",
        )
    else:
        engine.simulate_status_check(
            case_id=case_id,
            status_type=StatusType.WATCHLIST,
            entity_identifier=passport.document_number if passport else "UNKNOWN",
            source="NATIONAL_DB",
            status="CLEAN",
        )

    # Visa status
    if visa:
        engine.simulate_status_check(
            case_id=case_id,
            status_type=StatusType.VISA,
            entity_identifier=visa.document_number,
            source="VISA_SYSTEM",
            status="VALID",
        )

    # Passport status
    if passport:
        if scenario["id"] == "scenario_4":
            engine.simulate_status_check(
                case_id=case_id,
                status_type=StatusType.PASSPORT,
                entity_identifier=passport.document_number,
                source="PASSPORT_REGISTRY",
                status="REVOKED",
                adverse_reason="Reported stolen",
            )
        else:
            engine.simulate_status_check(
                case_id=case_id,
                status_type=StatusType.PASSPORT,
                entity_identifier=passport.document_number,
                source="PASSPORT_REGISTRY",
                status="VALID",
            )