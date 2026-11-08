"""Controlled vocabularies approved by the prototype design."""

from enum import StrEnum


class AdapterMode(StrEnum):
    MOCK = "mock"
    AZURE = "azure"


class ProcessingStatus(StrEnum):
    SUCCESSFUL = "successful"
    PARTIAL = "partial"
    FAILED = "failed"


RequestStatus = ProcessingStatus
DocumentStatus = ProcessingStatus
PayslipStatus = ProcessingStatus


class DocumentType(StrEnum):
    PAYSLIP = "payslip"
    PAY_SUMMARY = "pay_summary"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class BoundaryDecision(StrEnum):
    SAME_PAYSLIP = "same_payslip"
    NEW_PAYSLIP = "new_payslip"
    UNCERTAIN = "uncertain"


class BoundarySignalType(StrEnum):
    EMPLOYER = "employer"
    EMPLOYEE = "employee"
    PAY_PERIOD = "pay_period"
    HEADING = "heading"
    PAGE_CONTINUITY = "page_continuity"


class FieldStatus(StrEnum):
    PRESENT = "present"
    NOT_PRESENT = "not_present"
    UNREADABLE = "unreadable"
    NOT_APPLICABLE = "not_applicable"


class PayItemStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNREADABLE = "unreadable"


class MappingMethod(StrEnum):
    RULE = "rule"
    LLM = "llm"
    UNKNOWN = "unknown"


class GroupLabel(StrEnum):
    GROSS = "Gross"
    PAID_LEAVE = "Paid leave"
    ALLOWANCES = "Allowances"
    OVERTIME = "Overtime"
    BONUSES_AND_COMMISSIONS = "Bonuses and commissions"
    DIRECTORS_FEES = "Directors' fees"
    SALARY_SACRIFICE = "Salary sacrifice"
    LUMP_SUM_W = "Lump sum W"
    OTHER_LUMP_SUM_PAYMENTS = "Other lump sum payments"
    EMPLOYMENT_TERMINATION_PAYMENTS = "Employment termination payments"
    PAYG_WITHHOLDING = "PAYG withholding"
    SUPERANNUATION = "Superannuation"
    DEDUCTIONS = "Deductions"
    REIMBURSEMENTS = "Reimbursements"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class TotalType(StrEnum):
    GROSS_PAY = "gross_pay"
    NET_PAY = "net_pay"
    TAXABLE_GROSS = "taxable_gross"
    TOTAL_EARNINGS = "total_earnings"
    TOTAL_TAX = "total_tax"
    TOTAL_DEDUCTIONS = "total_deductions"
    TOTAL_SUPERANNUATION = "total_superannuation"
    OTHER = "other"
    UNKNOWN = "unknown"


class IssueScope(StrEnum):
    REQUEST = "request"
    DOCUMENT = "document"
    PAYSLIP = "payslip"
    FIELD = "field"
    ITEM = "item"
    RECONCILIATION = "reconciliation"


class ReconciliationStatus(StrEnum):
    MATCHED = "matched"
    MISMATCHED = "mismatched"
    UNABLE_TO_CHECK = "unable_to_check"


class RoundingAssessment(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    POSSIBLE = "possible"
    CONFIRMED = "confirmed"


class JudgeOutcome(StrEnum):
    NOT_RUN = "not_run"
    SUPPORTS_EXTRACTION = "supports_extraction"
    POSSIBLE_EXTRACTION_ERROR = "possible_extraction_error"
    POSSIBLE_RECONCILIATION_ITEM_SELECTION_ERROR = (
        "possible_reconciliation_item_selection_error"
    )
    INCONCLUSIVE = "inconclusive"


class TargetedRetryType(StrEnum):
    NONE = "none"
    EXTRACTION = "extraction"
    RECONCILIATION_ITEM_SELECTION = "reconciliation_item_selection"


class ReconciliationSourceType(StrEnum):
    PAY_ITEM = "pay_item"
    PRINTED_TOTAL = "printed_total"
