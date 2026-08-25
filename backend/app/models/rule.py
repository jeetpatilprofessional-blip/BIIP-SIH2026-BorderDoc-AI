# BIIP-SIH2026 Rule Model
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid


class RuleType(str, Enum):
    FIELD_REQUIRED = "FIELD_REQUIRED"
    FIELD_FORMAT = "FIELD_FORMAT"
    FIELD_RANGE = "FIELD_RANGE"
    DATE_VALIDITY = "DATE_VALIDITY"
    EXPIRY_CHECK = "EXPIRY_CHECK"
    CHECK_DIGIT = "CHECK_DIGIT"
    CROSS_FIELD = "CROSS_FIELD"
    DOCUMENT_RELATIONSHIP = "DOCUMENT_RELATIONSHIP"
    VISA_RULE = "VISA_RULE"
    PERMIT_RULE = "PERMIT_RULE"
    TRAVEL_CHRONOLOGY = "TRAVEL_CHRONOLOGY"


class RuleSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Rule(SQLModel, table=True):
    __tablename__ = "rules"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # Rule identification
    rule_code: str = Field(unique=True, index=True)  # e.g., "PASSPORT_EXPIRY", "VISA_PASSPORT_MATCH"
    name: str
    description: str

    # Rule classification
    rule_type: RuleType = Field(index=True)
    severity: RuleSeverity = Field(default=RuleSeverity.ERROR)

    # Applicability
    document_types: Optional[str] = Field(default=None)  # JSON array of DocumentType
    countries: Optional[str] = Field(default=None)  # JSON array of ISO country codes (null = all)

    # Rule logic (simplified for prototype - JSON-based)
    condition: str = Field()  # JSON expression
    error_message: str
    error_code: str

    # Evidence generation
    generates_evidence_type: Optional[str] = Field(default=None)  # e.g., "DOCUMENT_EXPIRED"
    evidence_severity: Optional[str] = Field(default=None)  # EvidenceSeverity

    # Versioning
    version: int = Field(default=1)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)