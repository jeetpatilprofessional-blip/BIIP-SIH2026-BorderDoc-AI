# BIIP-SIH2026 Rules Engine
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union
from sqlmodel import Session, select
import re
import json

from app.services.rules.models import (
    ValidationRule,
    RuleSet,
    RuleViolation,
    ValidationResult,
    RuleType,
    RuleSeverity,
    DocumentType,
    DEFAULT_RULES,
    load_rule_set,
)
from app.models.document import Document, DocumentType as ModelDocumentType
from app.models.document_field import DocumentField


class RulesEngine:
    """Rule-driven document validation engine"""

    def __init__(self, session: Session):
        self.session = session
        self.rule_sets = DEFAULT_RULES

    def validate_document(self, document: Document) -> ValidationResult:
        """Validate a single document against its rule set"""
        # Map model document type to rule document type
        rule_doc_type = self._map_document_type(document.document_type)
        rule_set = self.rule_sets.get(rule_doc_type)

        if not rule_set:
            return ValidationResult(
                document_id=document.id,
                document_type=rule_doc_type,
                is_valid=True,
                violations=[],
                warnings=[],
            )

        # Load all fields for this document
        fields = self.session.exec(
            select(DocumentField).where(DocumentField.document_id == document.id)
        ).all()

        field_dict = {f.field_name: f for f in fields}

        violations = []
        warnings = []
        field_results = {}

        # Apply each rule
        for rule in rule_set.rules:
            field = field_dict.get(rule.field_name)
            value = field.value if field else None

            rule_violations = self._apply_rule(rule, value, field_dict, document)

            for rv in rule_violations:
                if rv.severity in [RuleSeverity.ERROR, RuleSeverity.CRITICAL]:
                    violations.append(rv)
                else:
                    warnings.append(rv)

            # Track field result
            field_results[rule.field_name] = {
                "valid": len([v for v in rule_violations if v.severity in [RuleSeverity.ERROR, RuleSeverity.CRITICAL]]) == 0,
                "value": value,
                "violations": [v.model_dump() for v in rule_violations],
            }

        is_valid = len(violations) == 0

        return ValidationResult(
            document_id=document.id,
            document_type=rule_doc_type,
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            field_results=field_results,
        )

    def validate_case(self, case_id: str) -> List[ValidationResult]:
        """Validate all documents in a case"""
        documents = self.session.exec(
            select(Document).where(Document.case_id == case_id)
        ).all()

        results = []
        for doc in documents:
            result = self.validate_document(doc)
            results.append(result)

        return results

    def _map_document_type(self, model_type: ModelDocumentType) -> DocumentType:
        """Map model document type to rule document type"""
        mapping = {
            ModelDocumentType.PASSPORT: DocumentType.PASSPORT,
            ModelDocumentType.VISA: DocumentType.VISA,
            ModelDocumentType.NATIONAL_ID: DocumentType.NATIONAL_ID,
            ModelDocumentType.DRIVING_LICENCE: DocumentType.DRIVING_LICENSE,
        }
        return mapping.get(model_type, DocumentType.UNKNOWN)

    def _apply_rule(
        self,
        rule: ValidationRule,
        value: Optional[str],
        field_dict: Dict[str, DocumentField],
        document: Document,
    ) -> List[RuleViolation]:
        """Apply a single rule and return violations"""
        violations = []

        if rule.rule_type == RuleType.REQUIRED:
            if not value or not value.strip():
                violations.append(RuleViolation(
                    rule_id=rule.rule_id,
                    field_name=rule.field_name,
                    rule_type=rule.rule_type,
                    severity=rule.severity,
                    expected="non-empty value",
                    actual=value,
                    message=rule.error_message,
                    error_code=rule.error_code,
                ))

        elif rule.rule_type == RuleType.REGEX:
            if value and rule.regex_pattern:
                if not re.match(rule.regex_pattern, value.strip()):
                    violations.append(RuleViolation(
                        rule_id=rule.rule_id,
                        field_name=rule.field_name,
                        rule_type=rule.rule_type,
                        severity=rule.severity,
                        expected=f"match pattern {rule.regex_pattern}",
                        actual=value,
                        message=rule.error_message,
                        error_code=rule.error_code,
                    ))

        elif rule.rule_type == RuleType.DATE:
            if value and rule.date_format:
                try:
                    datetime.strptime(value.strip(), rule.date_format)
                except ValueError:
                    violations.append(RuleViolation(
                        rule_id=rule.rule_id,
                        field_name=rule.field_name,
                        rule_type=rule.rule_type,
                        severity=rule.severity,
                        expected=f"date in format {rule.date_format}",
                        actual=value,
                        message=rule.error_message,
                        error_code=rule.error_code,
                    ))

        elif rule.rule_type == RuleType.EXPIRY:
            if value and rule.date_format:
                try:
                    expiry = datetime.strptime(value.strip(), rule.date_format).date()
                    if expiry < date.today():
                        violations.append(RuleViolation(
                            rule_id=rule.rule_id,
                            field_name=rule.field_name,
                            rule_type=rule.rule_type,
                            severity=rule.severity,
                            expected="future date",
                            actual=value,
                            message=rule.error_message,
                            error_code=rule.error_code,
                        ))
                except ValueError:
                    # Date format error caught by DATE rule
                    pass

        elif rule.rule_type == RuleType.CROSS_FIELD:
            if value and rule.cross_field and rule.date_format:
                other_field = field_dict.get(rule.cross_field)
                other_value = other_field.value if other_field else None

                if other_value:
                    try:
                        val_date = datetime.strptime(value.strip(), rule.date_format).date()
                        other_date = datetime.strptime(other_value.strip(), rule.date_format).date()

                        # For expiry vs issue: expiry must be after
                        if rule.field_name in ["expiry_date", "expiry"] and rule.cross_field in ["issue_date", "issue"]:
                            if val_date <= other_date:
                                violations.append(RuleViolation(
                                    rule_id=rule.rule_id,
                                    field_name=rule.field_name,
                                    rule_type=rule.rule_type,
                                    severity=rule.severity,
                                    expected=f"after {rule.cross_field}",
                                    actual=f"{value} (other: {other_value})",
                                    message=rule.error_message,
                                    error_code=rule.error_code,
                                ))
                        # For birth vs issue: birth must be before
                        elif rule.field_name in ["birth_date", "date_of_birth"] and rule.cross_field in ["issue_date", "issue"]:
                            if val_date >= other_date:
                                violations.append(RuleViolation(
                                    rule_id=rule.rule_id,
                                    field_name=rule.field_name,
                                    rule_type=rule.rule_type,
                                    severity=rule.severity,
                                    expected=f"before {rule.cross_field}",
                                    actual=f"{value} (other: {other_value})",
                                    message=rule.error_message,
                                    error_code=rule.error_code,
                                ))
                    except ValueError:
                        pass

        elif rule.rule_type == RuleType.EXPRESSION:
            if value and rule.expression:
                # Build evaluation context
                context = self._build_expression_context(value, field_dict, document)

                try:
                    # WARNING: eval() used for prototype only - production should use safe evaluator
                    result = eval(rule.expression, {"__builtins__": {}}, context)
                    if not result:
                        violations.append(RuleViolation(
                            rule_id=rule.rule_id,
                            field_name=rule.field_name,
                            rule_type=rule.rule_type,
                            severity=rule.severity,
                            expected=rule.expression,
                            actual=value,
                            message=rule.error_message,
                            error_code=rule.error_code,
                        ))
                except Exception as e:
                    # Expression evaluation failed
                    violations.append(RuleViolation(
                        rule_id=rule.rule_id,
                        field_name=rule.field_name,
                        rule_type=rule.rule_type,
                        severity=RuleSeverity.WARNING,
                        expected=rule.expression,
                        actual=value,
                        message=f"Expression evaluation failed: {e}",
                        error_code="EXPRESSION_ERROR",
                    ))

        elif rule.rule_type == RuleType.CONDITIONAL:
            if rule.condition:
                context = self._build_expression_context(value, field_dict, document)
                try:
                    # Check if condition is met
                    condition_met = eval(rule.condition, {"__builtins__": {}}, context)
                    if condition_met:
                        # Apply the rule's main validation
                        # This is a meta-rule - could be extended
                        pass
                except Exception:
                    pass

        return violations

    def _build_expression_context(
        self,
        value: str,
        field_dict: Dict[str, DocumentField],
        document: Document,
    ) -> Dict[str, Any]:
        """Build context for expression evaluation"""
        context = {"value": value}

        # Add all field values
        for fname, field in field_dict.items():
            context[fname] = field.value

        # Add computed values
        if "birth_date" in field_dict:
            try:
                birth = datetime.strptime(field_dict["birth_date"].value.strip(), "%Y-%m-%d").date()
                context["age"] = (date.today() - birth).days // 365
            except (ValueError, AttributeError):
                context["age"] = None

        if "expiry_date" in field_dict:
            try:
                expiry = datetime.strptime(field_dict["expiry_date"].value.strip(), "%Y-%m-%d").date()
                context["days_to_expiry"] = (expiry - date.today()).days
                context["is_expired"] = expiry < date.today()
            except (ValueError, AttributeError):
                context["days_to_expiry"] = None
                context["is_expired"] = False

        # Document-level attributes
        context["mrz_valid"] = document.mrz_valid
        context["document_type"] = document.document_type.value if document.document_type else None

        return context


def validate_document(document: Document, session: Session) -> ValidationResult:
    """Convenience function"""
    engine = RulesEngine(session)
    return engine.validate_document(document)


def validate_case(case_id: str, session: Session) -> List[ValidationResult]:
    """Convenience function"""
    engine = RulesEngine(session)
    return engine.validate_case(case_id)