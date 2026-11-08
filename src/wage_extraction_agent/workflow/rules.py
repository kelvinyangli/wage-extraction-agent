"""Deterministic mapping, status and reconciliation rules."""

from __future__ import annotations

from decimal import Decimal

from pydantic import TypeAdapter, ValidationError

from wage_extraction_agent.models.common import CurrencyCode, Issue
from wage_extraction_agent.models.domain import (
    DocumentState,
    PayItem,
    PayslipState,
    PrintedTotal,
    ReconciliationCheckState,
)
from wage_extraction_agent.models.enums import (
    DocumentStatus,
    GroupLabel,
    IssueScope,
    MappingMethod,
    PayslipStatus,
    ReconciliationStatus,
    ReconciliationSourceType,
    RequestStatus,
    RoundingAssessment,
)


KNOWN_GROUP_MAPPINGS: tuple[tuple[str, GroupLabel], ...] = (
    ("PAYG", GroupLabel.PAYG_WITHHOLDING),
    ("TAX", GroupLabel.PAYG_WITHHOLDING),
    ("OVERTIME", GroupLabel.OVERTIME),
    ("OT ", GroupLabel.OVERTIME),
    ("ALLOWANCE", GroupLabel.ALLOWANCES),
    ("ANNUAL LEAVE", GroupLabel.PAID_LEAVE),
    ("PAID LEAVE", GroupLabel.PAID_LEAVE),
    ("SUPER", GroupLabel.SUPERANNUATION),
    ("DEDUCTION", GroupLabel.DEDUCTIONS),
    ("REIMBURSE", GroupLabel.REIMBURSEMENTS),
    ("BASE PAY", GroupLabel.GROSS),
    ("ORDINARY", GroupLabel.GROSS),
)


def known_group_label(label: str | None) -> GroupLabel | None:
    if not label:
        return None
    normalized = label.upper()
    for token, group in KNOWN_GROUP_MAPPINGS:
        if token in normalized:
            return group
    return None


def apply_known_mapping(item: PayItem) -> PayItem:
    group = known_group_label(item.original_label)
    if group is None:
        return item
    return item.model_copy(
        update={
            "group_label": group,
            "mapping_method": MappingMethod.RULE,
            "mapping_confidence": 1.0,
        }
    )


def reconcile_check(
    check: ReconciliationCheckState,
    items: list[PayItem],
    totals: list[PrintedTotal],
) -> ReconciliationCheckState:
    items_by_id = {item.item_id: item for item in items}
    totals_by_id = {total.total_id: total for total in totals}
    if check.printed_amount is None or not check.relationship.terms:
        return check.model_copy(
            update={
                "calculated_amount": None,
                "difference": None,
                "status": ReconciliationStatus.UNABLE_TO_CHECK,
                "reason": "Printed total or contributing relationship is unavailable.",
                "rounding_assessment": RoundingAssessment.NOT_APPLICABLE,
            }
        )

    calculated = Decimal("0")
    for term in check.relationship.terms:
        if term.source_type is ReconciliationSourceType.PAY_ITEM:
            source = items_by_id.get(term.source_record_id)
        else:
            source = totals_by_id.get(term.source_record_id)
            if term.source_record_id == check.printed_total_id:
                source = None
        if source is None or source.amount is None:
            return check.model_copy(
                update={
                    "calculated_amount": None,
                    "difference": None,
                    "status": ReconciliationStatus.UNABLE_TO_CHECK,
                    "reason": "A selected source record or amount is unavailable, or the relationship references its own target total.",
                    "rounding_assessment": RoundingAssessment.NOT_APPLICABLE,
                }
            )
        if check.currency is None or (
            source.currency is not None and source.currency != check.currency
        ):
            return check.model_copy(
                update={
                    "calculated_amount": None,
                    "difference": None,
                    "status": ReconciliationStatus.UNABLE_TO_CHECK,
                    "reason": "Selected item currencies are incompatible.",
                    "rounding_assessment": RoundingAssessment.NOT_APPLICABLE,
                }
            )
        calculated += source.amount * term.multiplier

    difference = calculated - check.printed_amount
    if difference == 0:
        status = ReconciliationStatus.MATCHED
        rounding = RoundingAssessment.NOT_APPLICABLE
        reason = "Exact decimal sum matches the printed total."
    else:
        status = ReconciliationStatus.MISMATCHED
        rounding = (
            RoundingAssessment.POSSIBLE
            if abs(difference) <= Decimal("0.01")
            else RoundingAssessment.NOT_APPLICABLE
        )
        reason = "Exact decimal sum does not match the printed total."
    return check.model_copy(
        update={
            "source_record_ids": [
                term.source_record_id for term in check.relationship.terms
            ],
            "calculated_amount": calculated,
            "difference": difference,
            "status": status,
            "reason": reason,
            "rounding_assessment": rounding,
        }
    )


def payslip_terminal_status(payslip: PayslipState) -> PayslipStatus:
    if not (
        payslip.employer.name
        or payslip.employee.name
        or payslip.line_items
        or payslip.totals
        or payslip.other_fields
    ):
        return PayslipStatus.FAILED if payslip.validation_errors else payslip.status
    if payslip.validation_errors or any(issue.review_required for issue in payslip.issues):
        return PayslipStatus.PARTIAL
    if any(
        check.status is not ReconciliationStatus.MATCHED
        for check in payslip.reconciliation_checks
    ):
        return PayslipStatus.PARTIAL
    return PayslipStatus.SUCCESSFUL


def derive_document_status(document: DocumentState) -> DocumentStatus:
    if not document.payslips:
        return DocumentStatus.FAILED
    if document.unresolved_sections or any(
        payslip.status is not PayslipStatus.SUCCESSFUL for payslip in document.payslips
    ):
        return DocumentStatus.PARTIAL
    return DocumentStatus.SUCCESSFUL


def derive_request_status(documents: list[DocumentState]) -> RequestStatus:
    usable = [document for document in documents if document.payslips]
    if not usable:
        return RequestStatus.FAILED
    if any(document.status is not DocumentStatus.SUCCESSFUL for document in documents):
        return RequestStatus.PARTIAL
    return RequestStatus.SUCCESSFUL


def review_issue(
    *, issue_id: str, code: str, message: str, pages: list[int]
) -> Issue:
    return Issue(
        issue_id=issue_id,
        issue_code=code,
        scope=IssueScope.RECONCILIATION,
        field_path=None,
        message=message,
        source_pages=pages,
        review_required=True,
    )


def validate_currency(value: object) -> str | None:
    if value is None:
        return None
    try:
        return TypeAdapter(CurrencyCode).validate_python(value)
    except ValidationError:
        return None
