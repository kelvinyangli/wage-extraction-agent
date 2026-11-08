"""Private workflow channels and structured LLM-stage responses."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal

from pydantic import Field
from typing_extensions import NotRequired, TypedDict

from wage_extraction_agent.models.common import StrictModel, ValidationErrorRecord
from wage_extraction_agent.models.domain import (
    BoundaryEvidence,
    DocumentState,
    PayslipState,
    TotalRelationship,
    UnresolvedSection,
)
from wage_extraction_agent.models.enums import GroupLabel, JudgeOutcome, MappingMethod
from wage_extraction_agent.models.state import RequestState


class SegmentationResult(StrictModel):
    payslips: list[BoundaryEvidence] = Field(default_factory=list)
    unresolved_sections: list[UnresolvedSection] = Field(default_factory=list)


class GroupClassificationResult(StrictModel):
    item_id: str
    group_label: GroupLabel
    mapping_method: Literal[MappingMethod.LLM]
    mapping_confidence: None = None


class RepairResult(StrictModel):
    patch: dict[str, Any] = Field(default_factory=dict)
    repaired_field_paths: list[str] = Field(default_factory=list)


class JudgeResult(StrictModel):
    judge_outcome: JudgeOutcome
    judge_reason: str
    affected_field_paths: list[str] = Field(default_factory=list)


class ExtractionRetryResult(StrictModel):
    patch: dict[str, Any] = Field(default_factory=dict)
    affected_field_paths: list[str] = Field(default_factory=list)


class WorkflowState(RequestState, total=False):
    """Business state plus private orchestration channels excluded from output."""

    expected_branch_ids: Annotated[set[str], operator.or_]
    completed_branch_ids: Annotated[set[str], operator.or_]
    segmented_document_refs: Annotated[set[str], operator.or_]
    response_json: dict[str, Any]
    output_path: str
    publication_complete: bool


class DocumentWork(TypedDict):
    request_id: str
    document: DocumentState


class PayslipWork(TypedDict):
    request_id: str
    document: DocumentState
    payslip: PayslipState
    raw_payload: NotRequired[dict[str, Any]]
    repair_count: NotRequired[int]
    valid_next: NotRequired[Literal["interpret", "reconcile"]]
    validation_errors: NotRequired[list[ValidationErrorRecord]]
    current_check_index: NotRequired[int]
    affected_field_paths: NotRequired[list[str]]


class UnresolvedWork(TypedDict):
    request_id: str
    document: DocumentState
    section: UnresolvedSection


class RelationshipBatch(StrictModel):
    relationships: list[TotalRelationship] = Field(default_factory=list)
