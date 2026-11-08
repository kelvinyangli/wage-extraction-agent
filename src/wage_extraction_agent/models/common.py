"""Shared validated value objects."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PlainSerializer,
    PositiveInt,
    StringConstraints,
    field_validator,
)

from wage_extraction_agent.models.enums import FieldStatus, IssueScope


DecimalValue = Annotated[
    Decimal,
    Field(allow_inf_nan=False),
    PlainSerializer(lambda value: format(value, "f"), return_type=str, when_used="json"),
]
Confidence = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
CurrencyCode = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z]{3}$", min_length=3, max_length=3),
]


def require_unique_ordered_pages(pages: list[int]) -> list[int]:
    """Reject duplicate or unsorted page references rather than silently changing them."""

    if pages != sorted(set(pages)):
        raise ValueError("page numbers must be unique and in ascending order")
    return pages


class StrictModel(BaseModel):
    """Base contract: reject undeclared fields and validate later assignments."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Coordinate(StrictModel):
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)


class EvidenceLocation(StrictModel):
    page_number: PositiveInt
    polygon: list[Coordinate] = Field(default_factory=list)
    text_offset: NonNegativeInt | None = None
    text_length: NonNegativeInt | None = None


class Issue(StrictModel):
    issue_id: str = Field(min_length=1)
    issue_code: str = Field(min_length=1)
    scope: IssueScope
    field_path: str | None = None
    message: str = Field(min_length=1)
    source_pages: list[PositiveInt] = Field(default_factory=list)
    review_required: bool

    _pages_are_unique_and_ordered = field_validator("source_pages")(
        require_unique_ordered_pages
    )


class FieldMetadata(StrictModel):
    status: FieldStatus
    source_page: PositiveInt | None = None
    source_location: EvidenceLocation | None = None
    ocr_confidence: Confidence | None = None
    issues: list[Issue] = Field(default_factory=list)


class ValidationErrorRecord(StrictModel):
    field_path: str = Field(min_length=1)
    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


class DocumentCounts(StrictModel):
    total: NonNegativeInt = 0
    successful: NonNegativeInt = 0
    partial: NonNegativeInt = 0
    failed: NonNegativeInt = 0


class PayslipCounts(StrictModel):
    detected: NonNegativeInt = 0
    successful: NonNegativeInt = 0
    partial: NonNegativeInt = 0
    failed: NonNegativeInt = 0
    unresolved: NonNegativeInt = 0


class ItemCounts(StrictModel):
    detected: NonNegativeInt = 0
    successful: NonNegativeInt = 0
    partial: NonNegativeInt = 0
    failed: NonNegativeInt = 0
    review_required: NonNegativeInt = 0


class ReconciliationCounts(StrictModel):
    matched: NonNegativeInt = 0
    mismatched: NonNegativeInt = 0
    unable_to_check: NonNegativeInt = 0


class ProcessingMetadata(StrictModel):
    documents: DocumentCounts = Field(default_factory=DocumentCounts)
    payslips: PayslipCounts = Field(default_factory=PayslipCounts)
    items: ItemCounts = Field(default_factory=ItemCounts)
    reconciliation: ReconciliationCounts = Field(default_factory=ReconciliationCounts)


class ComponentVersions(StrictModel):
    model: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    schema_: str = Field(alias="schema", min_length=1)
    mapping: str = Field(min_length=1)
    adapter: str = Field(min_length=1)
    mock_fixture: str | None = None

    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, populate_by_name=True
    )
