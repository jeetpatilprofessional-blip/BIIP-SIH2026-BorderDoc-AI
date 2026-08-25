"""
Unit tests for RulesEngine
Tests document validation rules: EXPIRY, FORMAT, CROSS_FIELD, WATCHLIST, VISA_VALIDITY, TRAVEL_HISTORY
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
from sqlmodel import Session, select

from app.services.rules.engine import RulesEngine
from app.services.rules.models import (
    ValidationRule, RuleSet, RuleViolation, ValidationResult,
    RuleType, RuleSeverity, DocumentType, DEFAULT_RULES
)
from app.models.document import Document, DocumentType as ModelDocumentType
from app.models.document_field import DocumentField
from app.models.case import Case


@pytest.fixture
def mock_session():
    session = Mock(spec=Session)
    return session


@pytest.fixture
def rules_engine(mock_session):
    return RulesEngine(mock_session)


def _setup_document_fields(mock_session, fields):
    """Helper to mock session.exec for DocumentField queries"""
    mock_result = Mock()
    mock_result.all.return_value = fields
    mock_session.exec.return_value = mock_result


@pytest.fixture
def sample_passport():
    """Create a valid passport document with fields"""
    doc = Document(
        id="doc-1",
        case_id="case-1",
        document_type=ModelDocumentType.PASSPORT,
        country_code="IND",
        document_number="P<IND12345678",
        mrz_raw="P<IND12345678<<DEMO<TRAVELER<<<<<<<<<<<<",
        mrz_valid=True,
        processing_status="COMPLETED",
    )
    fields = [
        DocumentField(id="f1", document_id="doc-1", field_name="surname", value="DEMO", confidence=0.95, source="OCR"),
        DocumentField(id="f2", document_id="doc-1", field_name="given_names", value="TRAVELER", confidence=0.95, source="OCR"),
        DocumentField(id="f3", document_id="doc-1", field_name="document_number", value="P1234567", confidence=0.98, source="OCR"),
        DocumentField(id="f4", document_id="doc-1", field_name="document_number", value="P1234567", confidence=0.99, source="MRZ", matched_field_id="f3"),
        DocumentField(id="f5", document_id="doc-1", field_name="nationality", value="IND", confidence=0.98, source="OCR"),
        DocumentField(id="f6", document_id="doc-1", field_name="nationality", value="IND", confidence=0.99, source="MRZ", matched_field_id="f5"),
        DocumentField(id="f7", document_id="doc-1", field_name="birth_date", value="1990-01-15", confidence=0.95, source="OCR"),
        DocumentField(id="f8", document_id="doc-1", field_name="birth_date", value="1990-01-15", confidence=0.99, source="MRZ", matched_field_id="f7"),
        DocumentField(id="f9", document_id="doc-1", field_name="sex", value="M", confidence=0.98, source="OCR"),
        DocumentField(id="f10", document_id="doc-1", field_name="sex", value="M", confidence=0.99, source="MRZ", matched_field_id="f9"),
        DocumentField(id="f11", document_id="doc-1", field_name="expiry_date", value=(datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d"), confidence=0.95, source="OCR"),
        DocumentField(id="f12", document_id="doc-1", field_name="expiry_date", value=(datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d"), confidence=0.99, source="MRZ", matched_field_id="f11"),
        DocumentField(id="f13", document_id="doc-1", field_name="issue_date", value="2020-01-15", confidence=0.95, source="OCR"),
        DocumentField(id="f14", document_id="doc-1", field_name="issuing_authority", value="GOVT OF INDIA", confidence=0.95, source="OCR"),
        DocumentField(id="f15", document_id="doc-1", field_name="mrz_raw", value="P<IND12345678<<DEMO<TRAVELER<<<<<<<<<<<<", confidence=0.99, source="MRZ"),
    ]
    doc.fields = fields
    return doc


@pytest.fixture
def expired_passport():
    """Create an expired passport document"""
    doc = Document(
        id="doc-2",
        case_id="case-1",
        document_type=ModelDocumentType.PASSPORT,
        country_code="IND",
        document_number="P<IND87654321",
        mrz_raw="P<IND87654321<<DEMO<TRAVELER<<<<<<<<<<<<",
        mrz_valid=True,
        processing_status="COMPLETED",
    )
    expiry = (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%d")
    fields = [
        DocumentField(id="f13", document_id="doc-2", field_name="surname", value="DEMO", confidence=0.95, source="OCR"),
        DocumentField(id="f14", document_id="doc-2", field_name="given_names", value="TRAVELER", confidence=0.95, source="OCR"),
        DocumentField(id="f15", document_id="doc-2", field_name="document_number", value="P87654321", confidence=0.98, source="OCR"),
        DocumentField(id="f16", document_id="doc-2", field_name="document_number", value="P87654321", confidence=0.99, source="MRZ", matched_field_id="f15"),
        DocumentField(id="f17", document_id="doc-2", field_name="expiry_date", value=expiry, confidence=0.95, source="OCR"),
        DocumentField(id="f18", document_id="doc-2", field_name="expiry_date", value=expiry, confidence=0.99, source="MRZ", matched_field_id="f17"),
        DocumentField(id="f19", document_id="doc-2", field_name="issue_date", value="2018-01-15", confidence=0.95, source="OCR"),
        DocumentField(id="f20", document_id="doc-2", field_name="birth_date", value="1990-01-15", confidence=0.95, source="OCR"),
        DocumentField(id="f21", document_id="doc-2", field_name="nationality", value="IND", confidence=0.95, source="OCR"),
        DocumentField(id="f22", document_id="doc-2", field_name="sex", value="M", confidence=0.95, source="OCR"),
        DocumentField(id="f23", document_id="doc-2", field_name="issuing_authority", value="GOVT OF INDIA", confidence=0.95, source="OCR"),
    ]
    doc.fields = fields
    return doc


@pytest.fixture
def mismatched_passport():
    """Create passport with OCR/MRZ mismatches"""
    doc = Document(
        id="doc-3",
        case_id="case-1",
        document_type=ModelDocumentType.PASSPORT,
        country_code="IND",
        document_number="P<IND11111111",
        mrz_raw="P<IND11111111<<DEMO<TRAVELER<<<<<<<<<<<<",
        mrz_valid=True,
        processing_status="COMPLETED",
    )
    doc.fields = [
        DocumentField(id="f19", document_id="doc-3", field_name="surname", value="DEMO", confidence=0.95, source="OCR"),
        DocumentField(id="f20", document_id="doc-3", field_name="surname", value="DIFFERENT", confidence=0.99, source="MRZ"),  # MISMATCH
        DocumentField(id="f21", document_id="doc-3", field_name="document_number", value="P1111111", confidence=0.98, source="OCR"),
        DocumentField(id="f22", document_id="doc-3", field_name="document_number", value="P2222222", confidence=0.99, source="MRZ"),  # MISMATCH
        DocumentField(id="f23", document_id="doc-3", field_name="expiry_date", value=(datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d"), confidence=0.95, source="OCR"),
        DocumentField(id="f24", document_id="doc-3", field_name="issue_date", value="2020-01-15", confidence=0.95, source="OCR"),
        DocumentField(id="f25", document_id="doc-3", field_name="birth_date", value="1990-01-15", confidence=0.95, source="OCR"),
        DocumentField(id="f26", document_id="doc-3", field_name="nationality", value="IND", confidence=0.95, source="OCR"),
        DocumentField(id="f27", document_id="doc-3", field_name="sex", value="M", confidence=0.95, source="OCR"),
        DocumentField(id="f28", document_id="doc-3", field_name="issuing_authority", value="GOVT OF INDIA", confidence=0.95, source="OCR"),
        DocumentField(id="f29", document_id="doc-3", field_name="mrz_raw", value="P<IND11111111<<DEMO<TRAVELER<<<<<<<<<<<<", confidence=0.99, source="MRZ"),
    ]
    return doc


class TestRulesEngine:
    """Test RulesEngine validation logic"""

    def test_validate_document_valid_passport(self, rules_engine, mock_session, sample_passport):
        """Test validation of a valid passport"""
        mock_session.get.return_value = sample_passport
        _setup_document_fields(mock_session, sample_passport.fields)

        result = rules_engine.validate_document(sample_passport)

        assert isinstance(result, ValidationResult)
        assert result.document_id == "doc-1"
        assert result.document_type == DocumentType.PASSPORT
        # Valid passport should have no critical violations
        critical_violations = [v for v in result.violations if v.severity == RuleSeverity.CRITICAL]
        assert len(critical_violations) == 0

    def test_validate_document_expired_passport(self, rules_engine, mock_session, expired_passport):
        """Test validation catches expired passport"""
        mock_session.get.return_value = expired_passport
        _setup_document_fields(mock_session, expired_passport.fields)

        result = rules_engine.validate_document(expired_passport)

        assert result.is_valid is False
        expiry_violations = [v for v in result.violations if v.rule_type == RuleType.EXPIRY]
        assert len(expiry_violations) > 0
        assert expiry_violations[0].severity == RuleSeverity.CRITICAL

    def test_validate_document_cross_field_mismatch(self, rules_engine, mock_session, mismatched_passport):
        """Test validation catches date cross-field mismatches (expiry before issue)"""
        # Create a passport with expiry before issue date
        doc = Document(
            id="doc-cross-mismatch",
            case_id="case-1",
            document_type=ModelDocumentType.PASSPORT,
            country_code="IND",
            document_number="P1111111",
            mrz_raw="P<IND11111111<<DEMO<TRAVELER<<<<<<<<<<<<",
            mrz_valid=True,
            processing_status="COMPLETED",
        )
        doc.fields = [
            DocumentField(id="f1", document_id="doc-cross-mismatch", field_name="surname", value="DEMO", confidence=0.95, source="OCR"),
            DocumentField(id="f2", document_id="doc-cross-mismatch", field_name="given_names", value="TRAVELER", confidence=0.95, source="OCR"),
            DocumentField(id="f3", document_id="doc-cross-mismatch", field_name="document_number", value="P1111111", confidence=0.98, source="OCR"),
            DocumentField(id="f4", document_id="doc-cross-mismatch", field_name="nationality", value="IND", confidence=0.98, source="OCR"),
            DocumentField(id="f5", document_id="doc-cross-mismatch", field_name="birth_date", value="1990-01-15", confidence=0.95, source="OCR"),
            DocumentField(id="f6", document_id="doc-cross-mismatch", field_name="sex", value="M", confidence=0.98, source="OCR"),
            DocumentField(id="f7", document_id="doc-cross-mismatch", field_name="expiry_date", value="2019-01-01", confidence=0.95, source="OCR"),  # Before issue
            DocumentField(id="f8", document_id="doc-cross-mismatch", field_name="issue_date", value="2020-01-15", confidence=0.95, source="OCR"),
            DocumentField(id="f9", document_id="doc-cross-mismatch", field_name="issuing_authority", value="GOVT OF INDIA", confidence=0.95, source="OCR"),
            DocumentField(id="f10", document_id="doc-cross-mismatch", field_name="mrz_raw", value="P<IND11111111<<DEMO<TRAVELER<<<<<<<<<<<<", confidence=0.99, source="MRZ"),
        ]
        mock_session.get.return_value = doc
        _setup_document_fields(mock_session, doc.fields)

        result = rules_engine.validate_document(doc)

        assert result.is_valid is False
        cross_field_violations = [v for v in result.violations if v.rule_type == RuleType.CROSS_FIELD]
        assert len(cross_field_violations) > 0
        assert cross_field_violations[0].severity == RuleSeverity.ERROR

    def test_apply_expiry_rule_valid(self, rules_engine, mock_session, sample_passport):
        """Test EXPIRY rule with valid (future) expiry"""
        _setup_document_fields(mock_session, sample_passport.fields)
        rule_set = DEFAULT_RULES[DocumentType.PASSPORT]
        rule = next(r for r in rule_set.rules if r.rule_type == RuleType.EXPIRY)
        violations = rules_engine._apply_rule(rule, None, {f.field_name: f for f in sample_passport.fields}, sample_passport)

        assert len(violations) == 0

    def test_apply_expiry_rule_expired(self, rules_engine, mock_session, expired_passport):
        """Test EXPIRY rule with expired document"""
        _setup_document_fields(mock_session, expired_passport.fields)
        rule_set = DEFAULT_RULES[DocumentType.PASSPORT]
        rule = next(r for r in rule_set.rules if r.rule_type == RuleType.EXPIRY)
        expiry_field = next(f for f in expired_passport.fields if f.field_name == "expiry_date")
        violations = rules_engine._apply_rule(rule, expiry_field.value, {f.field_name: f for f in expired_passport.fields}, expired_passport)

        assert len(violations) == 1
        assert violations[0].rule_type == RuleType.EXPIRY
        assert violations[0].severity == RuleSeverity.CRITICAL
        assert "expired" in violations[0].message.lower()

    def test_apply_expiry_rule_expiring_soon(self, rules_engine, mock_session):
        """Test EXPIRY rule with document expiring within 30 days"""
        # Current EXPIRY rule only checks if expired, not if expiring soon
        # This test verifies the current behavior - no violation for expiring soon
        doc = Document(
            id="doc-expiring",
            case_id="case-1",
            document_type=ModelDocumentType.PASSPORT,
            country_code="IND",
            document_number="P<IND99999999",
            mrz_valid=True,
            processing_status="COMPLETED",
        )
        expiry = (datetime.utcnow() + timedelta(days=15)).strftime("%Y-%m-%d")
        doc.fields = [
            DocumentField(id="f-exp", document_id="doc-expiring", field_name="expiry_date", value=expiry, confidence=0.95, source="OCR"),
        ]

        rule_set = DEFAULT_RULES[DocumentType.PASSPORT]
        rule = next(r for r in rule_set.rules if r.rule_type == RuleType.EXPIRY)
        violations = rules_engine._apply_rule(rule, expiry, {f.field_name: f for f in doc.fields}, doc)

        # Current implementation doesn't check for "expiring soon" - no violation expected
        assert len(violations) == 0

    def test_apply_format_rule_valid_mrz(self, rules_engine, mock_session, sample_passport):
        """Test FORMAT rule with valid MRZ"""
        _setup_document_fields(mock_session, sample_passport.fields)
        rule_set = DEFAULT_RULES[DocumentType.PASSPORT]
        rule = next(r for r in rule_set.rules if r.rule_type == RuleType.REGEX and r.field_name == "document_number")
        violations = rules_engine._apply_rule(rule, "P1234567", {f.field_name: f for f in sample_passport.fields}, sample_passport)

        assert len(violations) == 0

    def test_apply_format_rule_invalid_mrz(self, rules_engine):
        """Test FORMAT rule with invalid MRZ (contains special chars not in pattern)"""
        doc = Document(
            id="doc-invalid-mrz",
            case_id="case-1",
            document_type=ModelDocumentType.PASSPORT,
            country_code="IND",
            document_number="INVALID!",
            mrz_raw="INVALID MRZ FORMAT",
            mrz_valid=False,
            processing_status="COMPLETED",
        )
        doc.fields = [DocumentField(id="f1", document_id="doc-invalid-mrz", field_name="document_number", value="INVALID!", confidence=0.95, source="OCR")]

        rule_set = DEFAULT_RULES[DocumentType.PASSPORT]
        rule = next(r for r in rule_set.rules if r.rule_type == RuleType.REGEX and r.field_name == "document_number")
        violations = rules_engine._apply_rule(rule, "INVALID!", {f.field_name: f for f in doc.fields}, doc)

        assert len(violations) == 1
        assert violations[0].rule_type == RuleType.REGEX
        assert violations[0].severity == RuleSeverity.ERROR

    def test_apply_cross_field_rule_match(self, rules_engine, mock_session, sample_passport):
        """Test CROSS_FIELD rule with matching OCR/MRZ fields"""
        _setup_document_fields(mock_session, sample_passport.fields)
        rule_set = DEFAULT_RULES[DocumentType.PASSPORT]
        rule = next(r for r in rule_set.rules if r.rule_type == RuleType.CROSS_FIELD)
        violations = rules_engine._apply_rule(rule, "2025-06-15", {f.field_name: f for f in sample_passport.fields}, sample_passport)

        assert len(violations) == 0

    def test_apply_cross_field_rule_mismatch(self, rules_engine, mock_session, mismatched_passport):
        """Test CROSS_FIELD rule with expiry before issue (date mismatch)"""
        _setup_document_fields(mock_session, mismatched_passport.fields)
        rule_set = DEFAULT_RULES[DocumentType.PASSPORT]
        # Find the expiry after issue rule
        rule = next(r for r in rule_set.rules if r.rule_type == RuleType.CROSS_FIELD and r.cross_field == "issue_date")
        # Set expiry before issue to trigger violation
        violations = rules_engine._apply_rule(rule, "2019-01-01", {f.field_name: f for f in mismatched_passport.fields}, mismatched_passport)

        assert len(violations) > 0
        assert violations[0].rule_type == RuleType.CROSS_FIELD
        assert violations[0].severity == RuleSeverity.ERROR

    def test_apply_cross_field_rule_missing_mrz(self, rules_engine, mock_session):
        """Test CROSS_FIELD rule when MRZ fields are missing"""
        doc = Document(
            id="doc-no-mrz",
            case_id="case-1",
            document_type=ModelDocumentType.PASSPORT,
            country_code="IND",
            document_number="P<IND11111111",
            mrz_raw=None,
            mrz_valid=False,
            processing_status="COMPLETED",
        )
        doc.fields = [
            DocumentField(id="f1", document_id="doc-no-mrz", field_name="surname", value="DEMO", confidence=0.95, source="OCR"),
            DocumentField(id="f2", document_id="doc-no-mrz", field_name="expiry_date", value=(datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d"), confidence=0.95, source="OCR"),
        ]

        rule_set = DEFAULT_RULES[DocumentType.PASSPORT]
        rule = next(r for r in rule_set.rules if r.rule_type == RuleType.CROSS_FIELD)
        violations = rules_engine._apply_rule(rule, None, {f.field_name: f for f in doc.fields}, doc)

        # Should not fail if MRZ is not available - just skip
        assert len(violations) == 0

    def test_validate_case_multiple_documents(self, rules_engine, mock_session, sample_passport, expired_passport):
        """Test case-level validation with multiple documents"""
        # validate_case calls:
        # 1. select(Document).where(Document.case_id == case_id) -> .all() -> returns documents
        # 2. For each doc: validate_document -> select(DocumentField).where(DocumentField.document_id == doc.id) -> .all()

        # Set up exec calls in order
        mock_case_result = Mock()
        mock_case_result.all.return_value = [sample_passport, expired_passport]

        # Document fields for sample_passport
        mock_sp_fields = Mock()
        mock_sp_fields.all.return_value = sample_passport.fields

        # Document fields for expired_passport
        mock_ep_fields = Mock()
        mock_ep_fields.all.return_value = expired_passport.fields

        mock_session.exec.side_effect = [mock_case_result, mock_sp_fields, mock_ep_fields]

        result = rules_engine.validate_case("case-1")

        assert isinstance(result, list)
        # Should have violations from expired passport
        assert len(result) == 2
        assert any(not r.is_valid for r in result)

    def test_default_rules_exist_for_all_types(self):
        """Test that DEFAULT_RULES has entries for all document types"""
        assert DocumentType.PASSPORT in DEFAULT_RULES
        assert DocumentType.VISA in DEFAULT_RULES
        assert DocumentType.NATIONAL_ID in DEFAULT_RULES

        for doc_type, rule_set in DEFAULT_RULES.items():
            assert len(rule_set.rules) > 0
            rule_types = {r.rule_type for r in rule_set.rules}
            # Each doc type should have at least EXPIRY and REGEX (FORMAT)
            assert RuleType.EXPIRY in rule_types
            assert RuleType.REGEX in rule_types

    def test_visa_rules_include_visa_validity(self):
        """Test VISA rules include EXPIRY type (visa validity check)"""
        visa_rules = DEFAULT_RULES[DocumentType.VISA]
        rule_types = {r.rule_type for r in visa_rules.rules}
        assert RuleType.EXPIRY in rule_types

    def test_national_id_rules_include_format(self):
        """Test NATIONAL_ID rules include REGEX (format)"""
        nid_rules = DEFAULT_RULES[DocumentType.NATIONAL_ID]
        rule_types = {r.rule_type for r in nid_rules.rules}
        assert RuleType.REGEX in rule_types


class TestRuleModels:
    """Test rule data models"""

    def test_validation_rule_creation(self):
        """Test ValidationRule model creation"""
        rule = ValidationRule(
            rule_id="test-rule",
            rule_type=RuleType.EXPIRY,
            document_type=DocumentType.PASSPORT,
            field_name="expiry_date",
            severity=RuleSeverity.CRITICAL,
            error_message="Passport must not be expired",
            error_code="PASSPORT_EXPIRED",
            expression="expiry_date > now()",
        )
        assert rule.rule_type == RuleType.EXPIRY
        assert rule.severity == RuleSeverity.CRITICAL
        assert rule.rule_id == "test-rule"

    def test_rule_violation_creation(self):
        """Test RuleViolation model creation"""
        violation = RuleViolation(
            rule_id="test-rule",
            rule_type=RuleType.EXPIRY,
            severity=RuleSeverity.CRITICAL,
            field_name="expiry_date",
            expected="future date",
            actual="2020-01-01",
            message="Passport expired on 2020-01-01",
            error_code="PASSPORT_EXPIRED",
        )
        assert violation.severity == RuleSeverity.CRITICAL
        assert violation.field_name == "expiry_date"
        assert violation.error_code == "PASSPORT_EXPIRED"

    def test_validation_result_creation(self):
        """Test ValidationResult model creation"""
        result = ValidationResult(
            document_id="doc-1",
            document_type=DocumentType.PASSPORT,
            is_valid=True,
            violations=[],
        )
        assert result.is_valid is True
        assert result.violations == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])