"""LangGraph shared-state schema and parallel-document reducer."""

from __future__ import annotations

from typing import Annotated

from typing_extensions import TypedDict

from wage_extraction_agent.models.common import ComponentVersions, Issue, ProcessingMetadata
from wage_extraction_agent.models.domain import DocumentState
from wage_extraction_agent.models.enums import AdapterMode, RequestStatus


def merge_document_updates(
    current: list[DocumentState], updates: list[DocumentState]
) -> list[DocumentState]:
    """Merge branch results by stable document identity while preserving order."""

    merged = list(current)
    positions = {
        (document.document_id, document.source_document_ref): index
        for index, document in enumerate(merged)
    }
    for document in updates:
        identity = (document.document_id, document.source_document_ref)
        if identity in positions:
            existing = merged[positions[identity]]
            payslips = {item.payslip_id: item for item in existing.payslips}
            payslips.update({item.payslip_id: item for item in document.payslips})
            unresolved = {
                item.section_id: item for item in existing.unresolved_sections
            }
            unresolved.update(
                {item.section_id: item for item in document.unresolved_sections}
            )
            issues = {item.issue_id: item for item in existing.issues}
            issues.update({item.issue_id: item for item in document.issues})
            merged[positions[identity]] = document.model_copy(
                update={
                    "payslips": list(payslips.values()),
                    "unresolved_sections": list(unresolved.values()),
                    "issues": list(issues.values()),
                }
            )
        else:
            positions[identity] = len(merged)
            merged.append(document)
    return merged


class RequestState(TypedDict):
    request_id: str
    claim_number: str | None
    documents: Annotated[list[DocumentState], merge_document_updates]
    status: RequestStatus
    processing_metadata: ProcessingMetadata
    adapter_mode: AdapterMode
    max_concurrency: int
    versions: ComponentVersions
    issues: list[Issue]
