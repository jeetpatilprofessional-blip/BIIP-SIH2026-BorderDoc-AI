# BIIP-SIH2026 Document Validator
import time
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select

from app.services.document.models import (
    ValidationResult,
    ValidationRule,
    RuleViolation,
    ValidationSeverity,
)
from app.models.document import Document, DocumentType
from app.models.document_field import DocumentField
from app.models.rule import Rule, RuleType, RuleSeverity
from app.core.database import get_session


class DocumentValidator:
    """Configuration-driven document validation"""

    def __init__(self, session: Session):
        self.session = session
        self._rules_cache: Dict[str, List[Rule]] = {}

    def validate(self, document_id: str) -> ValidationResult:
        """Validate a document against all applicable rules"""
        start_time = time.time()

        document = self.session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Get document fields
        fields = self.session.exec(
            select(DocumentField).where(DocumentField.document_id == document_id)
        ).all()

        # Build field lookup
        field_map = {f.field_name: f for f in fields}

        # Get applicable rules
        rules = self._get_applicable_rules(document.document_type.value)
        violations = []
        warnings = []

        # Track per-field validation results
        field_results: Dict[str, Dict[str, Any]] = {}
        for fname in field_map:
            field_results[fname] = {"valid": True, "violations": []}

        for rule in rules:
            violation = self._evaluate_rule(rule, document, field_map)
            if violation:
                # Add to field results
                if violation.field_name in field_results:
                    field_results[violation.field_name]["valid"] = False
                    field_results[violation.field_name]["violations"].append({
                        "rule_code": violation.rule_code,
                        "message": violation.message,
                        "evidence_type": violation.evidence_type,
                    })

                if violation.severity == ValidationSeverity.ERROR:
                    violations.append(violation)
                else:
                    warnings.append(violation.message)

        is_valid = len(violations) == 0
        processing_time = (time.time() - start_time) * 1000

        return ValidationResult(
            document_id=document_id,
            document_type=document.document_type.value,
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            processing_time_ms=processing_time,
            rules_evaluated=len(rules),
            field_results=field_results,
        )

    def _get_applicable_rules(self, document_type: str) -> List[Rule]:
        """Get rules applicable to document type"""
        if document_type in self._rules_cache:
            return self._rules_cache[document_type]

        # Query active rules
        query = select(Rule).where(Rule.is_active == True)

        # Filter by document type (rules with null document_types apply to all)
        rules = self.session.exec(query).all()

        applicable = []
        for rule in rules:
            if rule.document_types:
                import json
                try:
                    doc_types = json.loads(rule.document_types)
                    if document_type in doc_types:
                        applicable.append(rule)
                except Exception:
                    pass
            else:
                applicable.append(rule)

        if not applicable:
            # Fallback to DEFAULT_RULES if DB rules table is unseeded
            from app.services.rules.models import DEFAULT_RULES, DocumentType as RuleDocType
            try:
                rule_doc_type = RuleDocType(document_type)
                rule_set = DEFAULT_RULES.get(rule_doc_type)
                if rule_set:
                    for vr in rule_set.rules:
                        import json
                        rule_type_val = vr.rule_type.value if hasattr(vr.rule_type, "value") else str(vr.rule_type)
                        sev_val = vr.severity.value if hasattr(vr.severity, "value") else str(vr.severity)
                        
                        if rule_type_val == "expiry":
                            cond = json.dumps({"type": "expiry", "field": vr.field_name})
                        elif rule_type_val == "required":
                            cond = json.dumps({"type": "required", "field": vr.field_name})
                        elif rule_type_val == "regex":
                            cond = json.dumps({"type": "regex", "field": vr.field_name, "pattern": vr.regex_pattern or ""})
                        elif rule_type_val == "date":
                            cond = json.dumps({"type": "date", "field": vr.field_name})
                        elif rule_type_val == "cross_field":
                            cond = json.dumps({"type": "cross_field", "field_a": vr.field_name, "field_b": vr.cross_field or ""})
                        else:
                            cond = json.dumps({"type": "expression", "expression": vr.expression or ""})

                        applicable.append(Rule(
                            id=f"default_{vr.rule_id}",
                            rule_code=vr.rule_id,
                            name=vr.rule_id,
                            description=vr.description or vr.error_message,
                            rule_type=rule_type_val,
                            severity=sev_val,
                            document_types=json.dumps([document_type]),
                            condition=cond,
                            error_message=vr.error_message,
                            error_code=vr.error_code,
                            generates_evidence_type="DOCUMENT_EXPIRED" if rule_type_val == "expiry" else "VALIDATION_FAILED",
                            is_active=True,
                        ))
            except Exception:
                pass

        self._rules_cache[document_type] = applicable
        return applicable


    def _evaluate_rule(
        self,
        rule: Rule,
        document: Document,
        field_map: Dict[str, DocumentField],
    ) -> Optional[RuleViolation]:
        """Evaluate a single rule against document fields"""
        import json

        try:
            condition = json.loads(rule.condition) if rule.condition else {}
        except:
            condition = {"type": "expression", "expression": rule.condition}

        condition_type = condition.get("type", "expression")

        if condition_type == "required":
            return self._check_required(rule, field_map, condition)
        elif condition_type == "regex":
            return self._check_regex(rule, field_map, condition)
        elif condition_type == "date":
            return self._check_date_validity(rule, field_map, condition)
        elif condition_type == "expiry":
            return self._check_expiry(rule, field_map, condition)
        elif condition_type == "check_digit":
            return self._check_check_digit(rule, field_map, condition)
        elif condition_type == "cross_field":
            return self._check_cross_field(rule, document, field_map, condition)
        elif condition_type == "expression":
            return self._check_expression(rule, field_map, condition)

        return None

    def _get_rule_severity(self, rule) -> ValidationSeverity:
        sev_str = rule.severity.value if hasattr(rule.severity, "value") else str(rule.severity)
        sev_str = sev_str.upper()
        if sev_str in ["CRITICAL", "HIGH", "ERROR"]:
            return ValidationSeverity.ERROR
        elif sev_str in ["MEDIUM", "LOW", "WARNING"]:
            return ValidationSeverity.WARNING
        return ValidationSeverity.INFO


    def _check_required(
        self, rule: Rule, field_map: Dict[str, DocumentField], condition: dict
    ) -> Optional[RuleViolation]:
        """Check if required field exists and has value"""
        field_name = condition.get("field", rule.rule_code.replace("_REQUIRED", "").replace("_required", "").lower())
        field_map_lookup = {
            "PASSPORT_REQUIRED_SURNAME": "surname",
            "PASSPORT_REQUIRED_GIVEN_NAMES": "given_names",
            "PASSPORT_REQUIRED_DOCUMENT_NUMBER": "document_number",
            "PASSPORT_REQUIRED_NATIONALITY": "nationality",
            "PASSPORT_REQUIRED_BIRTH_DATE": "birth_date",
            "PASSPORT_REQUIRED_SEX": "sex",
            "PASSPORT_REQUIRED_ISSUE_DATE": "issue_date",
            "PASSPORT_REQUIRED_EXPIRY_DATE": "expiry_date",
            "PASSPORT_REQUIRED_ISSUING_AUTHORITY": "issuing_authority",
            "VISA_REQUIRED_VISA_NUMBER": "visa_number",
            "VISA_REQUIRED_ISSUING_COUNTRY": "issuing_country",
            "VISA_REQUIRED_VISA_TYPE": "visa_type",
            "VISA_REQUIRED_ENTRY_DATE": "entry_date",
            "VISA_REQUIRED_EXPIRY_DATE": "expiry_date",
            "VISA_REQUIRED_ENTRIES": "number_of_entries",
            "NID_REQUIRED_ID_NUMBER": "id_number",
            "NID_REQUIRED_FULL_NAME": "full_name",
            "NID_REQUIRED_BIRTH_DATE": "birth_date",
            "NID_REQUIRED_ISSUE_DATE": "issue_date",
            "NID_REQUIRED_EXPIRY_DATE": "expiry_date",
        }
        field_name = field_map_lookup.get(rule.rule_code, field_name)
        field = field_map.get(field_name)

        if not field or not field.value:
            return RuleViolation(
                rule_code=rule.rule_code,
                rule_name=rule.name,
                severity=self._get_rule_severity(rule),
                field_name=field_name,
                expected="present",
                actual="missing",
                message=rule.error_message,
                evidence_type=rule.generates_evidence_type,
            )
        return None

    def _check_regex(
        self, rule: Rule, field_map: Dict[str, DocumentField], condition: dict
    ) -> Optional[RuleViolation]:
        """Check field against regex pattern"""
        field_map_lookup = {
            "PASSPORT_DOC_NUMBER_FORMAT": "document_number",
            "PASSPORT_NATIONALITY_FORMAT": "nationality",
            "PASSPORT_SEX_FORMAT": "sex",
            "VISA_ISSUING_COUNTRY_FORMAT": "issuing_country",
            "NID_ID_NUMBER_FORMAT": "id_number",
        }
        field_name = field_map_lookup.get(rule.rule_code, condition.get("field", ""))
        pattern = condition.get("pattern", "")
        field = field_map.get(field_name)

        if not field or not field.value:
            return None  # Handled by required check

        if not re.match(pattern, field.value):
            return RuleViolation(
                rule_code=rule.rule_code,
                rule_name=rule.name,
                severity=self._get_rule_severity(rule),
                field_name=field_name,
                expected=pattern,
                actual=field.value,
                message=rule.error_message,
                evidence_type=rule.generates_evidence_type,
            )
        return None

    def _check_date_validity(
        self, rule: Rule, field_map: Dict[str, DocumentField], condition: dict
    ) -> Optional[RuleViolation]:
        """Check if date is valid and in reasonable range"""
        field_map_lookup = {
            "PASSPORT_BIRTH_DATE_VALID": "birth_date",
            "PASSPORT_ISSUE_DATE_VALID": "issue_date",
            "PASSPORT_EXPIRY_DATE_VALID": "expiry_date",
            "VISA_ENTRY_DATE_VALID": "entry_date",
            "VISA_EXPIRY_DATE_VALID": "expiry_date",
            "NID_BIRTH_DATE_VALID": "birth_date",
            "NID_ISSUE_DATE_VALID": "issue_date",
            "NID_EXPIRY_DATE_VALID": "expiry_date",
        }
        field_name = field_map_lookup.get(rule.rule_code, condition.get("field", ""))
        field = field_map.get(field_name)

        if not field or not field.value:
            return None

        try:
            parsed_date = datetime.fromisoformat(field.value.replace("Z", "+00:00")).date()

            min_year = condition.get("min_year", 1900)
            max_year = condition.get("max_year", datetime.now().year + 10)

            if parsed_date.year < min_year or parsed_date.year > max_year:
                return RuleViolation(
                    rule_code=rule.rule_code,
                    rule_name=rule.name,
                    severity=self._get_rule_severity(rule),
                    field_name=field_name,
                    expected=f"year between {min_year} and {max_year}",
                    actual=str(parsed_date.year),
                    message=rule.error_message,
                    evidence_type=rule.generates_evidence_type,
                )
        except ValueError:
            return RuleViolation(
                rule_code=rule.rule_code,
                rule_name=rule.name,
                severity=self._get_rule_severity(rule),
                field_name=field_name,
                expected="valid ISO date",
                actual=field.value,
                message=rule.error_message,
                evidence_type=rule.generates_evidence_type,
            )

        return None

    def _check_expiry(
        self, rule: Rule, field_map: Dict[str, DocumentField], condition: dict
    ) -> Optional[RuleViolation]:
        """Check if document is expired"""
        field_map_lookup = {
            "PASSPORT_NOT_EXPIRED": "expiry_date",
            "VISA_NOT_EXPIRED": "expiry_date",
            "NID_NOT_EXPIRED": "expiry_date",
        }
        field_name = field_map_lookup.get(rule.rule_code, condition.get("field", ""))
        field = field_map.get(field_name)

        if not field or not field.value:
            return None

        try:
            expiry_date = datetime.fromisoformat(field.value.replace("Z", "+00:00")).date()
            today = date.today()

            if expiry_date < today:
                return RuleViolation(
                    rule_code=rule.rule_code,
                    rule_name=rule.name,
                    severity=self._get_rule_severity(rule),
                    field_name=field_name,
                    expected=f"after {today.isoformat()}",
                    actual=expiry_date.isoformat(),
                    message=rule.error_message,
                    evidence_type=rule.generates_evidence_type,
                )
        except ValueError:
            pass

        return None

    def _check_check_digit(
        self, rule: Rule, field_map: Dict[str, DocumentField], condition: dict
    ) -> Optional[RuleViolation]:
        """Validate check digit (e.g., MRZ)"""
        field_name = condition.get("field", rule.field if hasattr(rule, "field") else "")
        field = field_map.get(field_name)

        if not field or not field.value:
            return None

        return None

    def _check_cross_field(
        self,
        rule: Rule,
        document: Document,
        field_map: Dict[str, DocumentField],
        condition: dict,
    ) -> Optional[RuleViolation]:
        """Check consistency between fields (e.g., OCR vs MRZ)"""
        field_map_lookup = {
            "PASSPORT_EXPIRY_AFTER_ISSUE": ("expiry_date", "issue_date"),
            "PASSPORT_BIRTH_BEFORE_ISSUE": ("birth_date", "issue_date"),
            "VISA_EXPIRY_AFTER_ENTRY": ("expiry_date", "entry_date"),
            "NID_BIRTH_BEFORE_ISSUE": ("birth_date", "issue_date"),
        }
        fields = field_map_lookup.get(rule.rule_code, (condition.get("field_a", ""), condition.get("field_b", "")))
        field_a, field_b = fields
        comparison = condition.get("comparison", "equals")

        val_a = field_map.get(field_a, DocumentField(value="")).value
        val_b = field_map.get(field_b, DocumentField(value="")).value

        if not val_a or not val_b:
            return None

        match = False
        if comparison == "equals":
            match = self._normalize_for_comparison(val_a) == self._normalize_for_comparison(val_b)
        elif comparison == "not_equals":
            match = self._normalize_for_comparison(val_a) != self._normalize_for_comparison(val_b)
        elif comparison == "after":
            try:
                date_a = datetime.fromisoformat(val_a.replace("Z", "+00:00")).date()
                date_b = datetime.fromisoformat(val_b.replace("Z", "+00:00")).date()
                match = date_a > date_b
            except ValueError:
                match = False
        elif comparison == "before":
            try:
                date_a = datetime.fromisoformat(val_a.replace("Z", "+00:00")).date()
                date_b = datetime.fromisoformat(val_b.replace("Z", "+00:00")).date()
                match = date_a < date_b
            except ValueError:
                match = False

        if not match:
            return RuleViolation(
                rule_code=rule.rule_code,
                rule_name=rule.name,
                severity=self._get_rule_severity(rule),
                field_name=f"{field_a} vs {field_b}",
                expected=val_b,
                actual=val_a,
                message=rule.error_message,
                evidence_type=rule.generates_evidence_type,
            )
        return None

    def _check_expression(
        self, rule: Rule, field_map: Dict[str, DocumentField], condition: dict
    ) -> Optional[RuleViolation]:
        """Evaluate custom expression"""
        expression = condition.get("expression", "")

        for field_name, field in field_map.items():
            if field.value:
                expression = expression.replace(f"${field_name}", f"'{field.value}'")

        try:
            result = eval(expression, {"__builtins__": {}}, {})
            if not result:
                return RuleViolation(
                    rule_code=rule.rule_code,
                    rule_name=rule.name,
                    severity=self._get_rule_severity(rule),
                    field_name=rule.field if hasattr(rule, "field") else "",
                    message=rule.error_message,
                    evidence_type=rule.generates_evidence_type,
                )
        except:
            pass

        return None


    def _normalize_for_comparison(self, value: str) -> str:
        """Normalize value for comparison (handle transliteration, spacing, etc.)"""
        # Remove extra spaces, standardize case
        normalized = re.sub(r"\s+", " ", value.strip().upper())
        # Handle common transliteration differences
        normalized = normalized.replace("Ø", "O").replace("Å", "A").replace("Ä", "AE")
        normalized = normalized.replace("Ö", "OE").replace("Ü", "UE").replace("ß", "SS")
        return normalized


def validate_document(document_id: str, session: Session) -> ValidationResult:
    """Convenience function to validate a document"""
    validator = DocumentValidator(session)
    return validator.validate(document_id)