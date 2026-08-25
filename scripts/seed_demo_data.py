#!/usr/bin/env python3
"""
BIIP-SIH2026 Demo Data Seeder
Loads synthetic test data into database for demo scenarios
"""
import sys
import uuid
from datetime import datetime, date
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlmodel import Session, select
from app.core.database import engine
from app.models.case import Case
from app.models.person import Person
from app.models.document import Document, DocumentType
from app.models.document_field import DocumentField
from app.models.face_result import FaceResult, FaceMatchResult
from app.models.tamper_result import TamperResult
from app.models.evidence import EvidenceAtom, EvidenceSeverity, EvidenceSource, FreshnessState
from app.models.identity_graph import IdentityNode, IdentityEdge, NodeType, EdgeType
from app.models.audit import AuditLog
from app.models.sync_queue import SyncQueueItem, SyncOperationType, SyncStatus, SyncPriority
from app.models.status_cache import StatusCache, StatusType, FreshnessState as CacheFreshnessState
from app.services.audit.logger import AuditLogger


# Demo scenario data
SCENARIOS = [
    {
        "id": "scenario_1",
        "name": "Clean Traveler",
        "case_number": "DEMO-S1-001",
        "passport": {
            "doc_number": "P<IND12345678",
            "expiry": "2030-01-15",
            "dob": "1990-01-15",
            "mrz_valid": True,
        },
        "visa": {
            "doc_number": "VISA_IND_2024_ABC",
            "passport_number": "P<IND12345678",
            "expiry": "2025-01-10",
            "dob": "1990-01-15",
        },
        "face": {
            "match_score": 0.92,
            "match_result": FaceMatchResult.MATCH,
            "liveness": "LIVE",
        },
        "watchlist": "CLEAN",
        "recommendation": "LOW_CONCERN",
    },
    {
        "id": "scenario_2",
        "name": "Expired Passport",
        "case_number": "DEMO-S2-001",
        "passport": {
            "doc_number": "P<IND11111111",
            "expiry": "2020-01-15",
            "dob": "1990-01-15",
            "mrz_valid": True,
        },
        "visa": {
            "doc_number": "VISA_IND_2024_DEF",
            "passport_number": "P<IND11111111",
            "expiry": "2025-01-10",
            "dob": "1990-01-15",
        },
        "face": {
            "match_score": 0.89,
            "match_result": FaceMatchResult.MATCH,
            "liveness": "LIVE",
        },
        "watchlist": "CLEAN",
        "recommendation": "HIGH_CONCERN",
    },
    {
        "id": "scenario_3",
        "name": "Face Mismatch",
        "case_number": "DEMO-S3-001",
        "passport": {
            "doc_number": "P<IND22222222",
            "expiry": "2030-01-15",
            "dob": "1990-01-15",
            "mrz_valid": True,
        },
        "visa": {
            "doc_number": "VISA_IND_2024_GHI",
            "passport_number": "P<IND22222222",
            "expiry": "2025-01-10",
            "dob": "1990-01-15",
        },
        "face": {
            "match_score": 0.35,
            "match_result": FaceMatchResult.NO_MATCH,
            "liveness": "LIVE",
        },
        "watchlist": "CLEAN",
        "recommendation": "HIGH_CONCERN",
    },
    {
        "id": "scenario_4",
        "name": "Watchlist Hit",
        "case_number": "DEMO-S4-001",
        "passport": {
            "doc_number": "P<IND1234567",
            "expiry": "2030-01-15",
            "dob": "1990-01-15",
            "mrz_valid": True,
        },
        "visa": {
            "doc_number": "VISA_IND_2024_JKL",
            "passport_number": "P<IND1234567",
            "expiry": "2025-01-10",
            "dob": "1990-01-15",
        },
        "face": {
            "match_score": 0.91,
            "match_result": FaceMatchResult.MATCH,
            "liveness": "LIVE",
        },
        "watchlist": "WATCHLISTED",
        "recommendation": "HIGH_CONCERN",
    },
    {
        "id": "scenario_5",
        "name": "Document Tampering",
        "case_number": "DEMO-S5-001",
        "passport": {
            "doc_number": "P<IND33333333",
            "expiry": "2030-01-15",
            "dob": "1990-01-15",
            "mrz_valid": True,
            "tampered": True,
        },
        "visa": {
            "doc_number": "VISA_IND_2024_MNO",
            "passport_number": "P<IND33333333",
            "expiry": "2025-01-10",
            "dob": "1990-01-15",
        },
        "face": {
            "match_score": 0.28,
            "match_result": FaceMatchResult.NO_MATCH,
            "liveness": "LIVE",
        },
        "watchlist": "CLEAN",
        "recommendation": "HIGH_CONCERN",
    },
    {
        "id": "scenario_6",
        "name": "Identity Fragmentation",
        "case_number": "DEMO-S6-001",
        "passport": {
            "doc_number": "P<IND11111111",
            "expiry": "2030-01-15",
            "dob": "1990-01-15",
            "mrz_valid": True,
        },
        "visa": {
            "doc_number": "VISA_IND_2024_XYZ",
            "passport_number": "P<IND11111111",
            "expiry": "2025-01-10",
            "dob": "1991-01-15",  # CONFLICT!
        },
        "face": {
            "match_score": 0.90,
            "match_result": FaceMatchResult.MATCH,
            "liveness": "LIVE",
        },
        "watchlist": "CLEAN",
        "recommendation": "SECONDARY_INSPECTION",
    },
    {
        "id": "scenario_7",
        "name": "Offline Mode",
        "case_number": "DEMO-S7-001",
        "passport": {
            "doc_number": "P<IND44444444",
            "expiry": "2030-01-15",
            "dob": "1990-01-15",
            "mrz_valid": True,
        },
        "visa": {
            "doc_number": "VISA_IND_2024_OFF",
            "passport_number": "P<IND44444444",
            "expiry": "2025-01-10",
            "dob": "1990-01-15",
        },
        "face": {
            "match_score": 0.93,
            "match_result": FaceMatchResult.MATCH,
            "liveness": "LIVE",
        },
        "watchlist": "UNAVAILABLE",
        "recommendation": "INSUFFICIENT_EVIDENCE",
    },
]


def seed_scenario(session: Session, scenario: dict) -> str:
    """Seed a single scenario"""
    case_id = str(uuid.uuid4())
    person_id = str(uuid.uuid4())

    # Create case
    case = Case(
        id=case_id,
        case_number=scenario["case_number"],
        location="DEL-IMM-01",
        officer_id="DEMO-OFFICER",
        status="IN_PROGRESS",
    )
    session.add(case)

    # Create person
    person = Person(
        id=person_id,
        case_id=case_id,
        surname="DEMO",
        given_names="TRAVELER",
        birth_date=date(1990, 1, 15),
        nationality="IND",
        confidence=0.95,
    )
    session.add(person)

    # Create passport document
    passport_id = str(uuid.uuid4())
    passport = Document(
        id=passport_id,
        case_id=case_id,
        person_id=person_id,
        document_type=DocumentType.PASSPORT,
        country_code="IND",
        document_number=scenario["passport"]["doc_number"],
        mrz_raw=f"{scenario['passport']['doc_number']}<<DEMO<TRAVELER<<<<<<<<<<<<",
        mrz_valid=scenario["passport"]["mrz_valid"],
        processing_status="COMPLETED",
        image_path=f"/demo_data/documents/passports/{scenario['id']}_passport.svg",
    )
    session.add(passport)

    # Passport fields
    passport_fields = [
        ("surname", "DEMO", 0.95, "OCR"),
        ("given_names", "TRAVELER", 0.95, "OCR"),
        ("birth_date", scenario["passport"]["dob"], 0.98, "MRZ"),
        ("document_number", scenario["passport"]["doc_number"], 0.99, "MRZ"),
        ("nationality", "IND", 0.99, "MRZ"),
        ("sex", "M", 0.99, "MRZ"),
        ("expiry_date", scenario["passport"]["expiry"], 0.99, "MRZ"),
        ("issuing_state", "IND", 0.99, "MRZ"),
    ]
    for name, value, conf, source in passport_fields:
        session.add(DocumentField(
            document_id=passport_id,
            field_name=name,
            value=value,
            confidence=conf,
            source=source,
        ))

    # Create visa document
    visa_id = str(uuid.uuid4())
    visa = Document(
        id=visa_id,
        case_id=case_id,
        person_id=person_id,
        document_type=DocumentType.VISA,
        country_code="IND",
        document_number=scenario["visa"]["doc_number"],
        barcode_raw=f"VISA|IND|{scenario['id'].upper()}|TOURIST|SINGLE|{scenario['visa']['doc_number']}|{scenario['visa']['passport_number']}|DEMO|TRAVELER|{scenario['visa']['dob']}|IND|2024-01-10|{scenario['visa']['expiry']}|2024-01-15|2024-02-15|30|DEL|TOURISM|REF2024001",
        processing_status="COMPLETED",
        image_path=f"/demo_data/documents/visas/{scenario['id']}_visa.svg",
    )
    session.add(visa)

    # Visa fields
    visa_fields = [
        ("visa_number", scenario["visa"]["doc_number"], 0.98, "BARCODE"),
        ("passport_number", scenario["visa"]["passport_number"], 0.98, "BARCODE"),
        ("surname", "DEMO", 0.95, "OCR"),
        ("given_names", "TRAVELER", 0.95, "OCR"),
        ("birth_date", scenario["visa"]["dob"], 0.98, "BARCODE"),
        ("nationality", "IND", 0.99, "BARCODE"),
        ("visa_type", "TOURIST", 0.99, "BARCODE"),
        ("entry_type", "SINGLE", 0.99, "BARCODE"),
        ("issue_date", "2024-01-10", 0.99, "BARCODE"),
        ("expiry_date", scenario["visa"]["expiry"], 0.99, "BARCODE"),
        ("entry_date", "2024-01-15", 0.99, "BARCODE"),
        ("exit_date", "2024-02-15", 0.99, "BARCODE"),
        ("max_stay_days", "30", 0.99, "BARCODE"),
    ]
    for name, value, conf, source in visa_fields:
        session.add(DocumentField(
            document_id=visa_id,
            field_name=name,
            value=value,
            confidence=conf,
            source=source,
        ))

    # Create face result
    face_id = str(uuid.uuid4())
    face = FaceResult(
        id=face_id,
        case_id=case_id,
        document_id=passport_id,
        source_type="LIVE_CAPTURE",
        image_path=f"/demo_data/faces/{scenario['id']}_live.svg",
        match_score=scenario["face"]["match_score"],
        match_result=scenario["face"]["match_result"],
        compared_to_document_id=passport_id,
        liveness_result=scenario["face"]["liveness"],
        liveness_confidence=0.88,
        challenge_type="BLINK",
        challenge_passed=True,
        processing_status="COMPLETED",
    )
    session.add(face)

    # Create tamper result (only for scenario 5)
    if scenario["id"] == "scenario_5":
        tamper = TamperResult(
            document_id=passport_id,
            tamper_detected=True,
            anomaly_score=0.87,
            photo_substitution_score=0.92,
            details={
                "regions": [
                    {"region": "photo", "anomaly_score": 0.92, "details": "Photo substitution"},
                    {"region": "surname", "anomaly_score": 0.78, "details": "Font anomaly"},
                ]
            },
            processing_status="COMPLETED",
        )
        session.add(tamper)
    else:
        tamper = TamperResult(
            document_id=passport_id,
            tamper_detected=False,
            anomaly_score=0.02,
            processing_status="COMPLETED",
        )
        session.add(tamper)

    # Create evidence atoms (simplified)
    atoms = []

    # Document valid
    atoms.append(EvidenceAtom(
        case_id=case_id,
        evidence_type="DOCUMENT_VALID",
        severity=EvidenceSeverity.LOW,
        source=EvidenceSource.MRZ,
        confidence=0.95,
        description="Passport MRZ valid",
        freshness=FreshnessState.VERIFIED_FRESH,
    ))

    # Face match/mismatch
    if scenario["face"]["match_result"] == FaceMatchResult.MATCH:
        atoms.append(EvidenceAtom(
            case_id=case_id,
            evidence_type="FACE_MATCH",
            severity=EvidenceSeverity.LOW,
            source=EvidenceSource.FACE_VERIFICATION,
            confidence=scenario["face"]["match_score"],
            description=f"Face matches passport ({scenario['face']['match_score']})",
            freshness=FreshnessState.VERIFIED_FRESH,
        ))
    else:
        atoms.append(EvidenceAtom(
            case_id=case_id,
            evidence_type="FACE_MISMATCH",
            severity=EvidenceSeverity.HIGH,
            source=EvidenceSource.FACE_VERIFICATION,
            confidence=1.0 - scenario["face"]["match_score"],
            description=f"Face mismatch ({scenario['face']['match_score']})",
            freshness=FreshnessState.VERIFIED_FRESH,
        ))

    # Liveness
    atoms.append(EvidenceAtom(
        case_id=case_id,
        evidence_type="LIVENESS_PASS",
        severity=EvidenceSeverity.INFO,
        source=EvidenceSource.LIVENESS,
        confidence=0.88,
        description="Liveness challenge passed",
        freshness=FreshnessState.VERIFIED_FRESH,
    ))

    # Watchlist
    if scenario["watchlist"] == "WATCHLISTED":
        atoms.append(EvidenceAtom(
            case_id=case_id,
            evidence_type="WATCHLIST_HIT",
            severity=EvidenceSeverity.CRITICAL,
            source=EvidenceSource.WATCHLIST,
            confidence=0.99,
            description="Passport on INTERPOL SLTD",
            freshness=FreshnessState.CONFIRMED_ADVERSE,
        ))
    elif scenario["watchlist"] == "UNAVAILABLE":
        atoms.append(EvidenceAtom(
            case_id=case_id,
            evidence_type="WATCHLIST_CLEAN",
            severity=EvidenceSeverity.INFO,
            source=EvidenceSource.WATCHLIST,
            confidence=0.5,
            description="Central watchlist unreachable",
            freshness=FreshnessState.UNAVAILABLE,
        ))
    else:
        atoms.append(EvidenceAtom(
            case_id=case_id,
            evidence_type="WATCHLIST_CLEAN",
            severity=EvidenceSeverity.INFO,
            source=EvidenceSource.WATCHLIST,
            confidence=0.9,
            description="Not on watchlist",
            freshness=FreshnessState.VERIFIED_FRESH,
        ))

    # Cross-field conflict (scenario 6)
    if scenario["id"] == "scenario_6":
        atoms.append(EvidenceAtom(
            case_id=case_id,
            evidence_type="CROSS_FIELD_CONFLICT_DOB",
            severity=EvidenceSeverity.HIGH,
            source=EvidenceSource.RULE_ENGINE,
            confidence=0.95,
            description="DOB mismatch: passport=1990-01-15, visa=1991-01-15",
            freshness=FreshnessState.VERIFIED_FRESH,
        ))
        atoms.append(EvidenceAtom(
            case_id=case_id,
            evidence_type="IDENTITY_FRAGMENTATION",
            severity=EvidenceSeverity.HIGH,
            source=EvidenceSource.IDENTITY_GRAPH,
            confidence=0.9,
            description="Two person clusters detected",
            freshness=FreshnessState.VERIFIED_FRESH,
        ))

    # Tamper evidence (scenario 5)
    if scenario["id"] == "scenario_5":
        atoms.append(EvidenceAtom(
            case_id=case_id,
            evidence_type="DOCUMENT_TAMPER_PHOTO",
            severity=EvidenceSeverity.CRITICAL,
            source=EvidenceSource.TAMPER_DETECTION,
            confidence=0.92,
            description="Photo substitution detected (ELA: 0.92)",
            freshness=FreshnessState.VERIFIED_FRESH,
        ))

    for atom in atoms:
        session.add(atom)

    # Identity graph nodes
    person_node = IdentityNode(
        case_id=case_id,
        node_type=NodeType.PERSON,
        label="Person: DEMO TRAVELER",
        attributes={"surname": "DEMO", "given_names": "TRAVELER", "dob": "1990-01-15"},
        confidence=0.95,
    )
    session.add(person_node)
    session.flush()

    passport_node = IdentityNode(
        case_id=case_id,
        node_type=NodeType.DOCUMENT,
        label=f"Passport {scenario['passport']['doc_number']}",
        attributes={"doc_type": "PASSPORT", "doc_number": scenario["passport"]["doc_number"]},
        confidence=0.95,
        source_document_id=passport_id,
    )
    session.add(passport_node)
    session.flush()

    visa_node = IdentityNode(
        case_id=case_id,
        node_type=NodeType.DOCUMENT,
        label=f"Visa {scenario['visa']['doc_number']}",
        attributes={"doc_type": "VISA", "doc_number": scenario["visa"]["doc_number"]},
        confidence=0.95,
        source_document_id=visa_id,
    )
    session.add(visa_node)
    session.flush()

    face_node = IdentityNode(
        case_id=case_id,
        node_type=NodeType.FACE,
        label="Live Face Capture",
        attributes={"match_score": scenario["face"]["match_score"], "liveness": scenario["face"]["liveness"]},
        confidence=0.9,
        source_face_id=face_id,
    )
    session.add(face_node)
    session.flush()

    session.commit()  # Get IDs

    # Identity graph edges
    edges = [
        (passport_node.id, person_node.id, EdgeType.BELONGS_TO, "Passport belongs to person", 0.95),
        (visa_node.id, person_node.id, EdgeType.BELONGS_TO, "Visa belongs to person", 0.95),
        (visa_node.id, passport_node.id, EdgeType.VALIDATES, "Visa references passport", 0.9),
        (face_node.id, passport_node.id, EdgeType.MATCHES, f"Face matches passport ({scenario['face']['match_score']})", scenario["face"]["match_score"]),
    ]

    # Add conflict edge for scenario 6
    if scenario["id"] == "scenario_6":
        edges.append((passport_node.id, visa_node.id, EdgeType.CONFLICTS_WITH, "DOB conflict: 1990-01-15 vs 1991-01-15", 0.95))

    for src, tgt, etype, desc, conf in edges:
        session.add(IdentityEdge(
            case_id=case_id,
            source_node_id=src,
            target_node_id=tgt,
            edge_type=etype,
            description=desc,
            confidence=conf,
        ))

    # Status cache entries
    watchlist_freshness = CacheFreshnessState.VERIFIED_FRESH
    if scenario["watchlist"] == "WATCHLISTED":
        watchlist_status = "WATCHLISTED"
        watchlist_freshness = CacheFreshnessState.CONFIRMED_ADVERSE
    elif scenario["watchlist"] == "UNAVAILABLE":
        watchlist_status = "UNKNOWN"
        watchlist_freshness = CacheFreshnessState.UNAVAILABLE
    else:
        watchlist_status = "CLEAN"

    session.add(StatusCache(
        case_id=case_id,
        entity_identifier=scenario["passport"]["doc_number"],
        status_type=StatusType.WATCHLIST,
        status=watchlist_status,
        freshness=watchlist_freshness,
        source="INTERPOL_SLTD" if scenario["watchlist"] != "UNAVAILABLE" else "INTERPOL_SLTD",
        details={"scenario": scenario["id"]},
    ))

    session.add(StatusCache(
        case_id=case_id,
        entity_identifier=scenario["visa"]["doc_number"],
        status_type=StatusType.VISA,
        status="VALID" if scenario["watchlist"] != "UNAVAILABLE" else "UNKNOWN",
        freshness=CacheFreshnessState.VERIFIED_FRESH if scenario["watchlist"] != "UNAVAILABLE" else CacheFreshnessState.UNAVAILABLE,
        source="VISA_SYSTEM",
    ))

    session.add(StatusCache(
        case_id=case_id,
        entity_identifier=scenario["passport"]["doc_number"],
        status_type=StatusType.PASSPORT,
        status="VALID" if scenario["watchlist"] not in ["WATCHLISTED", "UNAVAILABLE"] else ("REVOKED" if scenario["watchlist"] == "WATCHLISTED" else "UNKNOWN"),
        freshness=CacheFreshnessState.VERIFIED_FRESH if scenario["watchlist"] != "UNAVAILABLE" else CacheFreshnessState.UNAVAILABLE,
        source="PASSPORT_REGISTRY",
    ))

    # Sync queue for scenario 7
    if scenario["id"] == "scenario_7":
        sync_items = [
            (SyncOperationType.STATUS_CHECK, scenario["passport"]["doc_number"], "WATCHLIST", SyncPriority.CRITICAL),
            (SyncOperationType.STATUS_CHECK, scenario["visa"]["doc_number"], "VISA", SyncPriority.HIGH),
            (SyncOperationType.STATUS_CHECK, scenario["passport"]["doc_number"], "PASSPORT", SyncPriority.HIGH),
        ]
        for op_type, entity, status_type, priority in sync_items:
            session.add(SyncQueueItem(
                case_id=case_id,
                operation_type=op_type,
                entity_identifier=entity,
                status_type=status_type,
                priority=priority,
                status=SyncStatus.PENDING,
            ))

    # Audit log entries
    audit_logger = AuditLogger(session)
    audit_logger.log_action(
        case_id=case_id,
        action="CASE_CREATED",
        actor_id="DEMO-SYSTEM",
        actor_type="SYSTEM",
        result="SUCCESS",
        details={"scenario": scenario["id"], "case_number": scenario["case_number"]},
    )
    audit_logger.log_action(
        case_id=case_id,
        action="DOCUMENT_UPLOADED",
        actor_id="DEMO-SYSTEM",
        actor_type="SYSTEM",
        result="SUCCESS",
        details={"document_type": "PASSPORT", "document_id": passport_id},
    )
    audit_logger.log_action(
        case_id=case_id,
        action="DOCUMENT_UPLOADED",
        actor_id="DEMO-SYSTEM",
        actor_type="SYSTEM",
        result="SUCCESS",
        details={"document_type": "VISA", "document_id": visa_id},
    )
    audit_logger.log_action(
        case_id=case_id,
        action="FACE_VERIFIED",
        actor_id="DEMO-SYSTEM",
        actor_type="SYSTEM",
        result="SUCCESS",
        details={"match_result": scenario["face"]["match_result"].value, "match_score": scenario["face"]["match_score"]},
    )

    session.commit()
    return case_id


def main():
    print("=" * 50)
    print("BIIP-SIH2026 Demo Data Seeder")
    print("=" * 50)

    with Session(engine) as session:
        # Clear existing demo data
        print("Clearing existing demo cases...")
        demo_cases = session.exec(select(Case).where(Case.case_number.like("DEMO-%"))).all()
        for case in demo_cases:
            session.delete(case)
        session.commit()
        print(f"Cleared {len(demo_cases)} existing demo cases")

        # Seed all scenarios
        for scenario in SCENARIOS:
            print(f"Seeding {scenario['name']} ({scenario['id']})...")
            case_id = seed_scenario(session, scenario)
            print(f"  Created case: {case_id}")

    print("\n✓ All demo data seeded successfully!")
    print("\nTo run scenarios via API:")
    print("  curl -X POST http://localhost:8000/api/demo/scenarios/scenario_1/run")
    print("  ... (scenario_1 through scenario_7)")


if __name__ == "__main__":
    main()