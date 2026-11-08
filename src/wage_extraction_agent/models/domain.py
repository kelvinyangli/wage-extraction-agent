"""Approved wage-extraction domain and response contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, NonNegativeInt, PositiveInt, field_validator, model_validator

from wage_extraction_agent.models.common import (
    ComponentVersions,
    Confidence,
    CurrencyCode,
    DecimalValue,
    EvidenceLocation,
    FieldMetadata,
    Issue,
    ProcessingMetadata,
    StrictModel,
    ValidationErrorRecord,
    require_unique_ordered_pages,
)
from wage_extraction_agent.models.enums import (
    AdapterMode,
    BoundaryDecision,
    BoundarySignalType,
    DocumentStatus,
    DocumentType,
    GroupLabel,
    JudgeOutcome,
    MappingMethod,
    PayItemStatus,
    PayslipStatus,
    ReconciliationStatus,
    ReconciliationSourceType,
    RequestStatus,
    RoundingAssessment,
    TargetedRetryType,
    TotalType,
)
from wage_extraction_agent.models.evidence import DocumentEvidence


class FlexibleField(StrictModel):
    section: str | None = None
    original_label: str | None = None
    raw_value: str | None = None
    source_page: PositiveInt
    issues: list[Issue] = Field(default_factory=list)


class LeaveBalance(StrictModel):
    original_label: str | None = None
    raw_value: str | None = None
    numeric_value: DecimalValue | None = None
    unit: str | None = None
    source_page: PositiveInt
    issues: list[Issue] = Field(default_factory=list)


class EmployerDetails(StrictModel):
    name: str | None = None
    abn: str | None = None
    fields: list[FlexibleField] = Field(default_factory=list)


class EmployeeDetails(StrictModel):
    name: str | None = None
    employee_id: str | None = None
    fields: list[FlexibleField] = Field(default_factory=list)


class PayPeriodDetails(StrictModel):
    start_date: str | None = None
    end_date: str | None = None
    payment_date: str | None = None
    frequency: str | None = None
    weeks_in_pay: DecimalValue | None = None


class EmploymentDetails(StrictModel):
    base_rate: DecimalValue | None = None
    base_hours: DecimalValue | None = None


class BoundarySignal(StrictModel):
    signal_type: BoundarySignalType
    source_value: str | None = None
    source_page: PositiveInt
    location: EvidenceLocation | None = None


class BoundaryEvidence(StrictModel):
    signals: list[BoundarySignal] = Field(default_factory=list)
    decision: BoundaryDecision
    reason: str = Field(min_length=1)
    source_pages: list[PositiveInt]

    _pages_are_unique_and_ordered = field_validator("source_pages")(
        require_unique_ordered_pages
    )


class UnresolvedSection(StrictModel):
    section_id: str = Field(min_length=1)
    source_pages: list[PositiveInt]
    raw_text: str | None = None
    readable_fields: list[FlexibleField] = Field(default_factory=list)
    reason: str = Field(min_length=1)
    issues: list[Issue] = Field(default_factory=list)

    _pages_are_unique_and_ordered = field_validator("source_pages")(
        require_unique_ordered_pages
    )


class PayItem(StrictModel):
    item_id: str = Field(min_length=1)
    status: PayItemStatus
    section: str | None = None
    original_code: str | None = None
    original_label: str | None = None
    group_label: GroupLabel
    date: str | None = None
    hours_or_units: DecimalValue | None = None
    rate: DecimalValue | None = None
    amount: DecimalValue | None = None
    ytd_amount: DecimalValue | None = None
    currency: CurrencyCode | None = None
    source_page: PositiveInt
    source_location: EvidenceLocation | None = None
    ocr_confidence: Confidence | None = None
    mapping_method: MappingMethod
    mapping_confidence: Confidence | None = None
    issues: list[Issue] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_uncalibrated_llm_confidence(self) -> "PayItem":
        if (
            self.mapping_method is MappingMethod.LLM
            and self.mapping_confidence is not None
        ):
            raise ValueError(
                "prototype LLM mappings must leave mapping_confidence as None"
            )
        return self


class PrintedTotal(StrictModel):
    total_id: str = Field(min_length=1)
    original_label: str | None = None
    total_type: TotalType
    amount: DecimalValue | None = None
    currency: CurrencyCode | None = None
    source_page: PositiveInt
    issues: list[Issue] = Field(default_factory=list)


class RelationshipTerm(StrictModel):
    source_type: ReconciliationSourceType
    source_record_id: str = Field(min_length=1)
    multiplier: Literal[1, -1]
    reason: str = Field(min_length=1)


class TotalRelationship(StrictModel):
    terms: list[RelationshipTerm] = Field(default_factory=list)
    explanation: str = Field(min_length=1)


class ReconciliationCheckState(StrictModel):
    check_id: str = Field(min_length=1)
    payslip_id: str = Field(min_length=1)
    source_record_ids: list[str] = Field(default_factory=list)
    printed_total_id: str = Field(min_length=1)
    relationship: TotalRelationship
    printed_amount: DecimalValue | None = None
    calculated_amount: DecimalValue | None = None
    difference: DecimalValue | None = None
    currency: CurrencyCode | None = None
    status: ReconciliationStatus
    reason: str = Field(min_length=1)
    rounding_assessment: RoundingAssessment
    source_pages: list[PositiveInt]
    judge_outcome: JudgeOutcome = JudgeOutcome.NOT_RUN
    judge_reason: str | None = None
    targeted_retry_type: TargetedRetryType = TargetedRetryType.NONE
    targeted_retry_count: int = Field(default=0, ge=0, le=1)
    validation_errors: list[ValidationErrorRecord] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)

    _pages_are_unique_and_ordered = field_validator("source_pages")(
        require_unique_ordered_pages
    )


class PayslipState(StrictModel):
    payslip_id: str = Field(min_length=1)
    document_id: str | None = None
    source_pages: list[PositiveInt]
    boundary_evidence: BoundaryEvidence
    employer: EmployerDetails = Field(default_factory=EmployerDetails)
    employee: EmployeeDetails = Field(default_factory=EmployeeDetails)
    pay_period: PayPeriodDetails = Field(default_factory=PayPeriodDetails)
    employment: EmploymentDetails = Field(default_factory=EmploymentDetails)
    currency: CurrencyCode | None = None
    field_metadata: dict[str, FieldMetadata] = Field(default_factory=dict)
    line_items: list[PayItem] = Field(default_factory=list)
    totals: list[PrintedTotal] = Field(default_factory=list)
    leave_balances: list[LeaveBalance] = Field(default_factory=list)
    other_fields: list[FlexibleField] = Field(default_factory=list)
    reconciliation_checks: list[ReconciliationCheckState] = Field(default_factory=list)
    validation_errors: list[ValidationErrorRecord] = Field(default_factory=list)
    schema_repair_count: int = Field(default=0, ge=0, le=1)
    status: PayslipStatus
    issues: list[Issue] = Field(default_factory=list)

    _pages_are_unique_and_ordered = field_validator("source_pages")(
        require_unique_ordered_pages
    )


class DocumentState(StrictModel):
    document_id: str | None = None
    source_document_ref: str = Field(min_length=1)
    page_count: NonNegativeInt
    document_type: DocumentType
    document_evidence: DocumentEvidence
    payslips: list[PayslipState] = Field(default_factory=list)
    unresolved_sections: list[UnresolvedSection] = Field(default_factory=list)
    status: DocumentStatus
    issues: list[Issue] = Field(default_factory=list)


class DocumentResult(StrictModel):
    document_id: str | None = None
    page_count: NonNegativeInt
    document_type: DocumentType
    payslips: list[PayslipState] = Field(default_factory=list)
    unresolved_sections: list[UnresolvedSection] = Field(default_factory=list)
    status: DocumentStatus
    issues: list[Issue] = Field(default_factory=list)

    @classmethod
    def from_state(cls, document: DocumentState) -> "DocumentResult":
        return cls(
            document_id=document.document_id,
            page_count=document.page_count,
            document_type=document.document_type,
            payslips=document.payslips,
            unresolved_sections=document.unresolved_sections,
            status=document.status,
            issues=document.issues,
        )


class ExtractionResponse(StrictModel):
    request_id: str = Field(min_length=1)
    claim_number: str | None = None
    documents: list[DocumentResult] = Field(default_factory=list)
    status: RequestStatus
    processing_metadata: ProcessingMetadata
    adapter_mode: AdapterMode
    max_concurrency: int = Field(default=2, gt=0)
    versions: ComponentVersions
    issues: list[Issue] = Field(default_factory=list)
