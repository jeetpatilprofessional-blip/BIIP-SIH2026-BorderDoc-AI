# BIIP-SIH2026 Rules Models
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
import json


class RuleType(str, Enum):
    REQUIRED = "required"
    REGEX = "regex"
    DATE = "date"
    EXPIRY = "expiry"
    CROSS_FIELD = "cross_field"
    EXPRESSION = "expression"
    CONDITIONAL = "conditional"


class RuleSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DocumentType(str, Enum):
    PASSPORT = "PASSPORT"
    VISA = "VISA"
    NATIONAL_ID = "NATIONAL_ID"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    UNKNOWN = "UNKNOWN"


class ValidationRule(BaseModel):
    """Single validation rule"""
    rule_id: str
    document_type: DocumentType = DocumentType.UNKNOWN
    field_name: str
    rule_type: RuleType
    severity: RuleSeverity = RuleSeverity.ERROR

    # Rule parameters
    regex_pattern: Optional[str] = None
    date_format: Optional[str] = None
    min_date: Optional[str] = None  # ISO format
    max_date: Optional[str] = None  # ISO format
    max_age_years: Optional[int] = None
    cross_field: Optional[str] = None  # Other field to compare
    expression: Optional[str] = None  # Python expression
    condition: Optional[str] = None  # Condition for conditional rule
    error_message: str
    error_code: str

    # Metadata
    description: str = ""
    version: str = "1.0"
    tags: List[str] = []


class RuleSet(BaseModel):
    """Collection of rules for a document type"""
    document_type: DocumentType
    version: str
    rules: List[ValidationRule]
    metadata: Dict[str, Any] = {}

    def get_rules_for_field(self, field_name: str) -> List[ValidationRule]:
        return [r for r in self.rules if r.field_name == field_name]

    def get_rules_by_type(self, rule_type: RuleType) -> List[ValidationRule]:
        return [r for r in self.rules if r.rule_type == rule_type]


class RuleViolation(BaseModel):
    """Result of a rule violation"""
    rule_id: str
    field_name: str
    rule_type: RuleType
    severity: RuleSeverity
    expected: Optional[str] = None
    actual: Optional[str] = None
    message: str
    error_code: str


class ValidationResult(BaseModel):
    """Result of validating a document"""
    document_id: str
    document_type: DocumentType
    is_valid: bool
    violations: List[RuleViolation] = []
    warnings: List[RuleViolation] = []
    field_results: Dict[str, Dict[str, Any]] = {}  # field_name -> {valid, value, violations}

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity in [RuleSeverity.ERROR, RuleSeverity.CRITICAL])

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == RuleSeverity.WARNING) + len(self.warnings)


# Default rule sets for common document types
DEFAULT_RULES = {
    DocumentType.PASSPORT: RuleSet(
        document_type=DocumentType.PASSPORT,
        version="1.0",
        rules=[
            # Required fields
            ValidationRule(
                rule_id="PASSPORT_REQUIRED_SURNAME",
                document_type=DocumentType.PASSPORT,
                field_name="surname",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Surname is required",
                error_code="MISSING_SURNAME",
            ),
            ValidationRule(
                rule_id="PASSPORT_REQUIRED_GIVEN_NAMES",
                document_type=DocumentType.PASSPORT,
                field_name="given_names",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Given names are required",
                error_code="MISSING_GIVEN_NAMES",
            ),
            ValidationRule(
                rule_id="PASSPORT_REQUIRED_DOCUMENT_NUMBER",
                document_type=DocumentType.PASSPORT,
                field_name="document_number",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Document number is required",
                error_code="MISSING_DOCUMENT_NUMBER",
            ),
            ValidationRule(
                rule_id="PASSPORT_REQUIRED_NATIONALITY",
                document_type=DocumentType.PASSPORT,
                field_name="nationality",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Nationality is required",
                error_code="MISSING_NATIONALITY",
            ),
            ValidationRule(
                rule_id="PASSPORT_REQUIRED_BIRTH_DATE",
                document_type=DocumentType.PASSPORT,
                field_name="birth_date",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Date of birth is required",
                error_code="MISSING_BIRTH_DATE",
            ),
            ValidationRule(
                rule_id="PASSPORT_REQUIRED_SEX",
                document_type=DocumentType.PASSPORT,
                field_name="sex",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Sex is required",
                error_code="MISSING_SEX",
            ),
            ValidationRule(
                rule_id="PASSPORT_REQUIRED_ISSUE_DATE",
                document_type=DocumentType.PASSPORT,
                field_name="issue_date",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Issue date is required",
                error_code="MISSING_ISSUE_DATE",
            ),
            ValidationRule(
                rule_id="PASSPORT_REQUIRED_EXPIRY_DATE",
                document_type=DocumentType.PASSPORT,
                field_name="expiry_date",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Expiry date is required",
                error_code="MISSING_EXPIRY_DATE",
            ),
            ValidationRule(
                rule_id="PASSPORT_REQUIRED_ISSUING_AUTHORITY",
                document_type=DocumentType.PASSPORT,
                field_name="issuing_authority",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Issuing authority is required",
                error_code="MISSING_ISSUING_AUTHORITY",
            ),

            # Format validation
            ValidationRule(
                rule_id="PASSPORT_DOC_NUMBER_FORMAT",
                document_type=DocumentType.PASSPORT,
                field_name="document_number",
                rule_type=RuleType.REGEX,
                severity=RuleSeverity.ERROR,
                regex_pattern=r"^[A-Z0-9<]{6,12}$",
                error_message="Invalid passport number format",
                error_code="INVALID_DOC_NUMBER_FORMAT",
            ),

            ValidationRule(
                rule_id="PASSPORT_NATIONALITY_FORMAT",
                document_type=DocumentType.PASSPORT,
                field_name="nationality",
                rule_type=RuleType.REGEX,
                severity=RuleSeverity.ERROR,
                regex_pattern=r"^[A-Z]{3}$",
                error_message="Nationality must be 3-letter ICAO code",
                error_code="INVALID_NATIONALITY_FORMAT",
            ),
            ValidationRule(
                rule_id="PASSPORT_SEX_FORMAT",
                document_type=DocumentType.PASSPORT,
                field_name="sex",
                rule_type=RuleType.REGEX,
                severity=RuleSeverity.ERROR,
                regex_pattern=r"^[MF]$",
                error_message="Sex must be M or F",
                error_code="INVALID_SEX_FORMAT",
            ),

            # Date validation
            ValidationRule(
                rule_id="PASSPORT_BIRTH_DATE_VALID",
                document_type=DocumentType.PASSPORT,
                field_name="birth_date",
                rule_type=RuleType.DATE,
                severity=RuleSeverity.ERROR,
                date_format="%Y-%m-%d",
                error_message="Invalid birth date format",
                error_code="INVALID_BIRTH_DATE",
            ),
            ValidationRule(
                rule_id="PASSPORT_ISSUE_DATE_VALID",
                document_type=DocumentType.PASSPORT,
                field_name="issue_date",
                rule_type=RuleType.DATE,
                severity=RuleSeverity.ERROR,
                date_format="%Y-%m-%d",
                error_message="Invalid issue date format",
                error_code="INVALID_ISSUE_DATE",
            ),
            ValidationRule(
                rule_id="PASSPORT_EXPIRY_DATE_VALID",
                document_type=DocumentType.PASSPORT,
                field_name="expiry_date",
                rule_type=RuleType.DATE,
                severity=RuleSeverity.ERROR,
                date_format="%Y-%m-%d",
                error_message="Invalid expiry date format",
                error_code="INVALID_EXPIRY_DATE",
            ),

            # Expiry check
            ValidationRule(
                rule_id="PASSPORT_NOT_EXPIRED",
                document_type=DocumentType.PASSPORT,
                field_name="expiry_date",
                rule_type=RuleType.EXPIRY,
                severity=RuleSeverity.CRITICAL,
                date_format="%Y-%m-%d",
                error_message="Passport has expired",
                error_code="PASSPORT_EXPIRED",
            ),

            # Cross-field: expiry after issue
            ValidationRule(
                rule_id="PASSPORT_EXPIRY_AFTER_ISSUE",
                document_type=DocumentType.PASSPORT,
                field_name="expiry_date",
                rule_type=RuleType.CROSS_FIELD,
                severity=RuleSeverity.ERROR,
                cross_field="issue_date",
                date_format="%Y-%m-%d",
                error_message="Expiry date must be after issue date",
                error_code="EXPIRY_BEFORE_ISSUE",
            ),

            # Cross-field: birth date before issue date
            ValidationRule(
                rule_id="PASSPORT_BIRTH_BEFORE_ISSUE",
                document_type=DocumentType.PASSPORT,
                field_name="birth_date",
                rule_type=RuleType.CROSS_FIELD,
                severity=RuleSeverity.ERROR,
                cross_field="issue_date",
                date_format="%Y-%m-%d",
                error_message="Birth date must be before issue date",
                error_code="BIRTH_AFTER_ISSUE",
            ),

            # Age check: person should be reasonable age
            ValidationRule(
                rule_id="PASSPORT_REASONABLE_AGE",
                document_type=DocumentType.PASSPORT,
                field_name="birth_date",
                rule_type=RuleType.EXPRESSION,
                severity=RuleSeverity.WARNING,
                expression="16 <= age <= 120",
                error_message="Age outside reasonable range (16-120)",
                error_code="UNREASONABLE_AGE",
            ),

            # MRZ fields if present
            ValidationRule(
                rule_id="PASSPORT_MRZ_VALID",
                document_type=DocumentType.PASSPORT,
                field_name="mrz_raw",
                rule_type=RuleType.EXPRESSION,
                severity=RuleSeverity.ERROR,
                expression="mrz_valid == True",
                error_message="MRZ check digits invalid",
                error_code="MRZ_CHECK_DIGITS_INVALID",
            ),
        ],
        metadata={"source": "ICAO Doc 9303", "applicable_regions": ["GLOBAL"]},
    ),

    DocumentType.VISA: RuleSet(
        document_type=DocumentType.VISA,
        version="1.0",
        rules=[
            ValidationRule(
                rule_id="VISA_REQUIRED_VISA_NUMBER",
                document_type=DocumentType.VISA,
                field_name="visa_number",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Visa number is required",
                error_code="MISSING_VISA_NUMBER",
            ),
            ValidationRule(
                rule_id="VISA_REQUIRED_ISSUING_COUNTRY",
                document_type=DocumentType.VISA,
                field_name="issuing_country",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Issuing country is required",
                error_code="MISSING_ISSUING_COUNTRY",
            ),
            ValidationRule(
                rule_id="VISA_REQUIRED_VISA_TYPE",
                document_type=DocumentType.VISA,
                field_name="visa_type",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Visa type is required",
                error_code="MISSING_VISA_TYPE",
            ),
            ValidationRule(
                rule_id="VISA_REQUIRED_ENTRY_DATE",
                document_type=DocumentType.VISA,
                field_name="entry_date",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Entry date is required",
                error_code="MISSING_ENTRY_DATE",
            ),
            ValidationRule(
                rule_id="VISA_REQUIRED_EXPIRY_DATE",
                document_type=DocumentType.VISA,
                field_name="expiry_date",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Expiry date is required",
                error_code="MISSING_EXPIRY_DATE",
            ),
            ValidationRule(
                rule_id="VISA_REQUIRED_ENTRIES",
                document_type=DocumentType.VISA,
                field_name="number_of_entries",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.ERROR,
                error_message="Number of entries is required",
                error_code="MISSING_ENTRIES",
            ),

            ValidationRule(
                rule_id="VISA_ISSUING_COUNTRY_FORMAT",
                document_type=DocumentType.VISA,
                field_name="issuing_country",
                rule_type=RuleType.REGEX,
                severity=RuleSeverity.ERROR,
                regex_pattern=r"^[A-Z]{3}$",
                error_message="Issuing country must be 3-letter ICAO code",
                error_code="INVALID_ISSUING_COUNTRY",
            ),

            ValidationRule(
                rule_id="VISA_ENTRY_DATE_VALID",
                document_type=DocumentType.VISA,
                field_name="entry_date",
                rule_type=RuleType.DATE,
                severity=RuleSeverity.ERROR,
                date_format="%Y-%m-%d",
                error_message="Invalid entry date format",
                error_code="INVALID_ENTRY_DATE",
            ),

            ValidationRule(
                rule_id="VISA_EXPIRY_DATE_VALID",
                document_type=DocumentType.VISA,
                field_name="expiry_date",
                rule_type=RuleType.DATE,
                severity=RuleSeverity.ERROR,
                date_format="%Y-%m-%d",
                error_message="Invalid expiry date format",
                error_code="INVALID_EXPIRY_DATE",
            ),

            ValidationRule(
                rule_id="VISA_NOT_EXPIRED",
                document_type=DocumentType.VISA,
                field_name="expiry_date",
                rule_type=RuleType.EXPIRY,
                severity=RuleSeverity.CRITICAL,
                date_format="%Y-%m-%d",
                error_message="Visa has expired",
                error_code="VISA_EXPIRED",
            ),

            ValidationRule(
                rule_id="VISA_EXPIRY_AFTER_ENTRY",
                document_type=DocumentType.VISA,
                field_name="expiry_date",
                rule_type=RuleType.CROSS_FIELD,
                severity=RuleSeverity.ERROR,
                cross_field="entry_date",
                error_message="Expiry date must be after entry date",
                error_code="EXPIRY_BEFORE_ENTRY",
            ),

            ValidationRule(
                rule_id="VISA_ENTRIES_POSITIVE",
                document_type=DocumentType.VISA,
                field_name="number_of_entries",
                rule_type=RuleType.EXPRESSION,
                severity=RuleSeverity.ERROR,
                expression="entries > 0",
                error_message="Number of entries must be positive",
                error_code="INVALID_ENTRIES_COUNT",
            ),
        ],
        metadata={"source": "Generic visa standards"},
    ),

    DocumentType.NATIONAL_ID: RuleSet(
        document_type=DocumentType.NATIONAL_ID,
        version="1.0",
        rules=[
            ValidationRule(
                rule_id="NID_REQUIRED_ID_NUMBER",
                document_type=DocumentType.NATIONAL_ID,
                field_name="id_number",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="ID number is required",
                error_code="MISSING_ID_NUMBER",
            ),
            ValidationRule(
                rule_id="NID_REQUIRED_FULL_NAME",
                document_type=DocumentType.NATIONAL_ID,
                field_name="full_name",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Full name is required",
                error_code="MISSING_FULL_NAME",
            ),
            ValidationRule(
                rule_id="NID_REQUIRED_BIRTH_DATE",
                document_type=DocumentType.NATIONAL_ID,
                field_name="birth_date",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Date of birth is required",
                error_code="MISSING_BIRTH_DATE",
            ),
            ValidationRule(
                rule_id="NID_REQUIRED_ISSUE_DATE",
                document_type=DocumentType.NATIONAL_ID,
                field_name="issue_date",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Issue date is required",
                error_code="MISSING_ISSUE_DATE",
            ),
            ValidationRule(
                rule_id="NID_REQUIRED_EXPIRY_DATE",
                document_type=DocumentType.NATIONAL_ID,
                field_name="expiry_date",
                rule_type=RuleType.REQUIRED,
                severity=RuleSeverity.CRITICAL,
                error_message="Expiry date is required",
                error_code="MISSING_EXPIRY_DATE",
            ),

            ValidationRule(
                rule_id="NID_ID_NUMBER_FORMAT",
                document_type=DocumentType.NATIONAL_ID,
                field_name="id_number",
                rule_type=RuleType.REGEX,
                severity=RuleSeverity.ERROR,
                regex_pattern=r"^[A-Z0-9]{8,14}$",
                error_message="Invalid ID number format",
                error_code="INVALID_ID_NUMBER_FORMAT",
            ),

            ValidationRule(
                rule_id="NID_BIRTH_DATE_VALID",
                document_type=DocumentType.NATIONAL_ID,
                field_name="birth_date",
                rule_type=RuleType.DATE,
                severity=RuleSeverity.ERROR,
                date_format="%Y-%m-%d",
                error_message="Invalid birth date format",
                error_code="INVALID_BIRTH_DATE",
            ),

            ValidationRule(
                rule_id="NID_ISSUE_DATE_VALID",
                document_type=DocumentType.NATIONAL_ID,
                field_name="issue_date",
                rule_type=RuleType.DATE,
                severity=RuleSeverity.ERROR,
                date_format="%Y-%m-%d",
                error_message="Invalid issue date format",
                error_code="INVALID_ISSUE_DATE",
            ),

            ValidationRule(
                rule_id="NID_EXPIRY_DATE_VALID",
                document_type=DocumentType.NATIONAL_ID,
                field_name="expiry_date",
                rule_type=RuleType.DATE,
                severity=RuleSeverity.ERROR,
                date_format="%Y-%m-%d",
                error_message="Invalid expiry date format",
                error_code="INVALID_EXPIRY_DATE",
            ),

            ValidationRule(
                rule_id="NID_NOT_EXPIRED",
                document_type=DocumentType.NATIONAL_ID,
                field_name="expiry_date",
                rule_type=RuleType.EXPIRY,
                severity=RuleSeverity.CRITICAL,
                date_format="%Y-%m-%d",
                error_message="National ID has expired",
                error_code="NID_EXPIRED",
            ),

            ValidationRule(
                rule_id="NID_BIRTH_BEFORE_ISSUE",
                document_type=DocumentType.NATIONAL_ID,
                field_name="birth_date",
                rule_type=RuleType.CROSS_FIELD,
                severity=RuleSeverity.ERROR,
                cross_field="issue_date",
                error_message="Birth date must be before issue date",
                error_code="BIRTH_AFTER_ISSUE",
            ),

            ValidationRule(
                rule_id="NID_REASONABLE_AGE",
                document_type=DocumentType.NATIONAL_ID,
                field_name="birth_date",
                rule_type=RuleType.EXPRESSION,
                severity=RuleSeverity.WARNING,
                expression="16 <= age <= 120",
                error_message="Age outside reasonable range",
                error_code="UNREASONABLE_AGE",
            ),
        ],
        metadata={"source": "National ID standards"},
    ),
}


def load_rule_set(document_type: DocumentType) -> RuleSet:
    """Load rule set for document type"""
    return DEFAULT_RULES.get(document_type, RuleSet(
        document_type=document_type,
        version="1.0",
        rules=[],
    ))


def get_all_rules() -> Dict[DocumentType, RuleSet]:
    return DEFAULT_RULES