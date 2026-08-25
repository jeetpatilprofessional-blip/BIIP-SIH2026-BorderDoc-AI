# BIIP-SIH2026 Document Validation Models
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class RuleViolation(BaseModel):
    """A single rule violation"""
    rule_code: str
    rule_name: str
    severity: ValidationSeverity
    field_name: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    message: str
    evidence_type: Optional[str] = None  # For generating evidence atoms


class ValidationResult(BaseModel):
    """Complete validation result for a document"""
    document_id: str
    document_type: str
    is_valid: bool
    violations: List[RuleViolation] = []
    warnings: List[str] = []
    processing_time_ms: float
    rules_evaluated: int
    field_results: Dict[str, Dict[str, Any]] = {}  # Per-field validation results


class ValidationRule(BaseModel):
    """Configuration-driven validation rule"""
    rule_code: str
    name: str
    description: str
    document_types: List[str]  # Document types this applies to
    countries: Optional[List[str]] = None  # ISO country codes, null = all
    severity: ValidationSeverity = ValidationSeverity.ERROR

    # Rule logic (simplified expression)
    field: str
    condition: str  # e.g., "required", "regex:^[A-Z]{3}[0-9]{6}$", "date_before:today"
    params: Dict[str, Any] = {}

    # Evidence generation
    generates_evidence_type: Optional[str] = None
    evidence_severity: Optional[str] = None