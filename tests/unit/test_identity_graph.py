"""
Unit tests for Identity Graph Builder
Tests node/edge creation, conflict detection, face clustering
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from sqlmodel import Session, select

from app.services.identity_graph.builder import build_identity_graph
from app.models.identity_graph import IdentityNode, IdentityEdge
from app.models.document import Document, DocumentType as ModelDocumentType
from app.models.document_field import DocumentField
from app.models.face_result import FaceResult, FaceMatchResult, LivenessResult
from app.models.case import Case


@pytest.fixture
def mock_session():
    session = Mock(spec=Session)
    return session


@pytest.fixture
def person_obj():
    """Create a person object for testing"""
    from app.models.person import Person
    return Person(
        id="person-1",
        case_id="case-1",
        primary_name="DEMO TRAVELER",
        primary_dob="1990-01-15",
        primary_nationality="IND",
        primary_gender="M",
        identity_confidence=0.9,
    )


@pytest.fixture
def case_with_documents(person_obj):
    """Create a case with passport and visa documents"""
    case = Case(id="case-1", case_number="TEST-001")

    passport = Document(
        id="doc-passport",
        case_id="case-1",
        document_type=ModelDocumentType.PASSPORT,
        country_code="IND",
        document_number="P<IND12345678",
        mrz_raw="P<IND12345678<<DEMO<TRAVELER<<<<<<<<<<<<",
        mrz_valid=True,
        processing_status="COMPLETED",
    )
    passport.fields = [
        DocumentField(id="pf1", document_id="doc-passport", field_name="surname", value="DEMO", confidence=0.95, source="OCR"),
        DocumentField(id="pf2", document_id="doc-passport", field_name="given_names", value="TRAVELER", confidence=0.95, source="OCR"),
        DocumentField(id="pf3", document_id="doc-passport", field_name="date_of_birth", value="1990-01-15", confidence=0.95, source="OCR"),
        DocumentField(id="pf4", document_id="doc-passport", field_name="passport_number", value="P<IND12345678", confidence=0.98, source="OCR"),
    ]

    visa = Document(
        id="doc-visa",
        case_id="case-1",
        document_type=ModelDocumentType.VISA,
        country_code="IND",
        document_number="VISA_IND_2024_ABC",
        barcode_raw="VISA|IND|SCENARIO_1|TOURIST|SINGLE",
        processing_status="COMPLETED",
    )
    visa.fields = [
        DocumentField(id="vf1", document_id="doc-visa", field_name="visa_number", value="VISA_IND_2024_ABC", confidence=0.95, source="OCR"),
        DocumentField(id="vf2", document_id="doc-visa", field_name="date_of_birth", value="1990-01-15", confidence=0.95, source="OCR"),
        DocumentField(id="vf3", document_id="doc-visa", field_name="passport_number", value="P<IND12345678", confidence=0.95, source="OCR"),
    ]

    case.documents = [passport, visa]
    case.person = person_obj
    return case


@pytest.fixture
def case_with_conflicts():
    """Create a case with conflicting documents (identity fragmentation)"""
    from app.models.person import Person

    case = Case(id="case-2", case_number="TEST-002")

    # Create a person for this case
    person_obj_2 = Person(
        id="person-2",
        case_id="case-2",
        primary_name="DEMO TRAVELER",
        primary_dob="1990-01-15",
        primary_nationality="IND",
        primary_gender="M",
        identity_confidence=0.9,
    )

    passport = Document(
        id="doc-passport-2",
        case_id="case-2",
        document_type=ModelDocumentType.PASSPORT,
        country_code="IND",
        document_number="P<IND11111111",
        mrz_valid=True,
        processing_status="COMPLETED",
    )
    passport.fields = [
        DocumentField(id="pf5", document_id="doc-passport-2", field_name="surname", value="DEMO", confidence=0.95, source="OCR"),
        DocumentField(id="pf6", document_id="doc-passport-2", field_name="given_names", value="TRAVELER", confidence=0.95, source="OCR"),
        DocumentField(id="pf7", document_id="doc-passport-2", field_name="date_of_birth", value="1990-01-15", confidence=0.95, source="OCR"),
        DocumentField(id="pf8", document_id="doc-passport-2", field_name="passport_number", value="P<IND11111111", confidence=0.98, source="OCR"),
    ]

    visa = Document(
        id="doc-visa-2",
        case_id="case-2",
        document_type=ModelDocumentType.VISA,
        country_code="IND",
        document_number="VISA_IND_2024_XYZ",
        barcode_raw="VISA|IND|SCENARIO_6|TOURIST|SINGLE",
        processing_status="COMPLETED",
    )
    visa.fields = [
        DocumentField(id="vf4", document_id="doc-visa-2", field_name="visa_number", value="VISA_IND_2024_XYZ", confidence=0.95, source="OCR"),
        DocumentField(id="vf5", document_id="doc-visa-2", field_name="date_of_birth", value="1991-01-15", confidence=0.95, source="OCR"),  # CONFLICT!
        DocumentField(id="vf6", document_id="doc-visa-2", field_name="passport_number", value="P<IND11111111", confidence=0.95, source="OCR"),
    ]

    case.documents = [passport, visa]
    case.person = person_obj_2
    return case

    case.documents = [passport, visa]
    return case


class TestIdentityGraphBuilder:
    """Test identity graph building"""

    def _setup_mock_session(self, mock_session, person_obj, documents, face_results=None):
        """Helper to set up mock session with all needed exec calls"""
        # The builder makes these exec calls in order:
        # 1. select(Person).where(Person.case_id == case_id) -> .first()
        # 2. select(Document).where(Document.case_id == case_id) -> .all()
        # 3. For each document: select(DocumentField).where(DocumentField.document_id == doc.id) -> .all()
        # 4. select(FaceResult).where(FaceResult.case_id == case_id) -> .all()
        # 5. For cross-document edges: select(DocumentField) for passport and visa
        # 6. For conflicts: select(DocumentField) for each field type PER DOCUMENT (5 field_types * num_docs)
        # 7. _persist_graph: select(IdentityNode).where(IdentityNode.case_id == case_id) -> .all()
        # 8. _persist_graph: select(IdentityEdge).where(IdentityEdge.case_id == case_id) -> .all()

        mock_exec_results = []

        # Call 1: Person query
        mock_person = Mock()
        mock_person.first.return_value = person_obj
        mock_exec_results.append(mock_person)

        # Call 2: Documents query
        mock_docs = Mock()
        mock_docs.all.return_value = documents
        mock_exec_results.append(mock_docs)

        # Call 3+: DocumentField queries for each document (for _create_document_node)
        for doc in documents:
            mock_fields = Mock()
            mock_fields.all.return_value = doc.fields
            mock_exec_results.append(mock_fields)

        # FaceResults query
        mock_faces = Mock()
        mock_faces.all.return_value = face_results or []
        mock_exec_results.append(mock_faces)

        # Cross-document edges: DocumentField queries for passport and visa
        passports = [d for d in documents if d.document_type.value == 'PASSPORT']
        visas = [d for d in documents if d.document_type.value == 'VISA']
        for passport in passports:
            mock_pfields = Mock()
            mock_pfields.all.return_value = passport.fields
            mock_exec_results.append(mock_pfields)
        for visa in visas:
            mock_vfields = Mock()
            mock_vfields.all.return_value = visa.fields
            mock_exec_results.append(mock_vfields)

        # Conflict detection: DocumentField queries for each field type PER DOCUMENT
        field_types = ["date_of_birth", "passport_number", "nationality", "surname", "given_names"]
        for field_type in field_types:
            for doc in documents:
                mock_cfields = Mock()
                # Collect fields of this type from this document
                matching_fields = []
                for f in doc.fields:
                    if f.field_name == field_type:
                        matching_fields.append(f)
                mock_cfields.all.return_value = matching_fields
                mock_exec_results.append(mock_cfields)

        # _persist_graph: existing nodes query
        mock_existing_nodes = Mock()
        mock_existing_nodes.all.return_value = []
        mock_exec_results.append(mock_existing_nodes)

        # _persist_graph: existing edges query
        mock_existing_edges = Mock()
        mock_existing_edges.all.return_value = []
        mock_exec_results.append(mock_existing_edges)

        mock_session.exec.side_effect = mock_exec_results

    def test_build_graph_creates_person_node(self, mock_session, case_with_documents, person_obj):
        """Test that a PERSON node is created"""
        self._setup_mock_session(mock_session, person_obj, case_with_documents.documents, [])

        build_identity_graph("case-1", mock_session)

        # Verify PERSON node creation was attempted
        add_calls = [call for call in mock_session.add.call_args_list
                     if call.args and hasattr(call.args[0], 'node_type')]
        person_nodes = [call.args[0] for call in add_calls
                        if hasattr(call.args[0], 'node_type') and call.args[0].node_type == 'PERSON']
        assert len(person_nodes) >= 1

    def test_build_graph_creates_document_nodes(self, mock_session, case_with_documents, person_obj):
        """Test that DOCUMENT nodes are created for each document"""
        self._setup_mock_session(mock_session, person_obj, case_with_documents.documents, [])

        build_identity_graph("case-1", mock_session)

        doc_nodes = [call.args[0] for call in mock_session.add.call_args_list
                     if hasattr(call.args[0], 'node_type') and call.args[0].node_type in ('PASSPORT', 'VISA')]
        assert len(doc_nodes) >= 2  # passport + visa

    def test_build_graph_creates_belongs_to_edges(self, mock_session, case_with_documents, person_obj):
        """Test that BELONGS_TO edges link documents to person"""
        self._setup_mock_session(mock_session, person_obj, case_with_documents.documents, [])

        build_identity_graph("case-1", mock_session)

        edges = [call.args[0] for call in mock_session.add.call_args_list
                 if hasattr(call.args[0], 'edge_type') and call.args[0].edge_type == 'BELONGS_TO']
        assert len(edges) >= 2

    def test_build_graph_creates_validates_edges(self, mock_session, case_with_documents, person_obj):
        """Test that REFERENCES edges link visa to passport"""
        self._setup_mock_session(mock_session, person_obj, case_with_documents.documents, [])

        build_identity_graph("case-1", mock_session)

        edges = [call.args[0] for call in mock_session.add.call_args_list
                 if hasattr(call.args[0], 'edge_type') and call.args[0].edge_type == 'REFERENCES']
        assert len(edges) >= 1

    def test_build_graph_detects_date_of_birth_conflict(self, mock_session, case_with_conflicts):
        """Test that CONFLICTS_WITH edge is created for DOB mismatch"""
        from app.models.person import Person
        person_2 = Person(
            id="person-2",
            case_id="case-2",
            primary_name="DEMO TRAVELER",
            primary_dob="1990-01-15",
            primary_nationality="IND",
            primary_gender="M",
            identity_confidence=0.9,
        )
        self._setup_mock_session(mock_session, person_2, case_with_conflicts.documents, [])

        build_identity_graph("case-2", mock_session)

        conflict_edges = [call.args[0] for call in mock_session.add.call_args_list
                          if hasattr(call.args[0], 'edge_type') and call.args[0].edge_type == 'CONFLICTS_WITH']
        assert len(conflict_edges) >= 1
        # Check conflict is about date_of_birth - description is in properties (Python dict string)
        conflict = conflict_edges[0]
        import ast
        props = ast.literal_eval(conflict.properties) if conflict.properties else {}
        assert 'date_of_birth' in str(props).lower() or 'dob' in str(props).lower()

    def test_build_graph_creates_face_nodes(self, mock_session, case_with_documents, person_obj):
        """Test that FACE nodes are created from face results"""
        face_result = FaceResult(
            id="face-1",
            case_id="case-1",
            source_type="LIVE_CAPTURE",
            image_path="/faces/live.jpg",
            match_score=0.92,
            match_result=FaceMatchResult.MATCH,
            compared_to_document_id="doc-passport",
            liveness_result=LivenessResult.LIVE,
            liveness_confidence=0.88,
            quality_score=0.9,
        )
        self._setup_mock_session(mock_session, person_obj, case_with_documents.documents, [face_result])

        build_identity_graph("case-1", mock_session)

        face_nodes = [call.args[0] for call in mock_session.add.call_args_list
                      if hasattr(call.args[0], 'node_type') and call.args[0].node_type == 'FACE']
        assert len(face_nodes) >= 1

    def test_build_graph_creates_matches_edge_for_face(self, mock_session, case_with_documents, person_obj):
        """Test that MATCHES edge links face to document"""
        face_result = FaceResult(
            id="face-1",
            case_id="case-1",
            source_type="LIVE_CAPTURE",
            image_path="/faces/live.jpg",
            match_score=0.92,
            match_result=FaceMatchResult.MATCH,
            compared_to_document_id="doc-passport",
            liveness_result=LivenessResult.LIVE,
            liveness_confidence=0.88,
            quality_score=0.9,
        )
        self._setup_mock_session(mock_session, person_obj, case_with_documents.documents, [face_result])

        build_identity_graph("case-1", mock_session)

        match_edges = [call.args[0] for call in mock_session.add.call_args_list
                       if hasattr(call.args[0], 'edge_type') and call.args[0].edge_type == 'MATCHES']
        assert len(match_edges) >= 1


class TestIdentityGraphModels:
    """Test identity graph data models"""

    def test_identity_node_creation(self):
        """Test IdentityNode model"""
        node = IdentityNode(
            id="node-1",
            case_id="case-1",
            node_type="PERSON",
            label="Person: DEMO TRAVELER",
            attributes={"surname": "DEMO", "given_names": "TRAVELER"},
            confidence=0.95,
        )
        assert node.node_type == "PERSON"
        assert node.confidence == 0.95

    def test_identity_edge_creation(self):
        """Test IdentityEdge model"""
        edge = IdentityEdge(
            id="edge-1",
            case_id="case-1",
            source_node_id="node-1",
            target_node_id="node-2",
            edge_type="BELONGS_TO",
            description="Passport belongs to person",
            confidence=0.9,
        )
        assert edge.edge_type == "BELONGS_TO"
        assert edge.confidence == 0.9


class TestFaceClustering:
    """Test face clustering for identity fragmentation detection"""

    def test_multiple_faces_same_person(self, mock_session):
        """Test clustering when multiple faces match same person"""
        pass  # Would need more complex mocking

    def test_multiple_faces_different_persons(self, mock_session):
        """Test clustering detects different persons (fragmentation)"""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])