"""Adapter protocols and mock fault vocabulary."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from wage_extraction_agent.models.evidence import DocumentEvidence


class PromptStage(StrEnum):
    SEGMENT_DOCUMENTS = "segment_documents"
    EXTRACT_PAYSLIP = "extract_payslip"
    CLASSIFY_UNFAMILIAR_GROUP_LABELS = "classify_unfamiliar_group_labels"
    SCHEMA_REPAIR_ONCE = "schema_repair_once"
    INTERPRET_TOTAL_RELATIONSHIPS = "interpret_total_relationships"
    LLM_AS_A_JUDGE = "llm_as_a_judge"
    RETRY_AFFECTED_EXTRACTION = "retry_affected_extraction"
    RETRY_RECONCILIATION_ITEM_SELECTION = (
        "retry_reconciliation_item_selection"
    )


class FaultMode(StrEnum):
    TIMEOUT = "timeout"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    MALFORMED = "malformed"


class DocumentIntelligenceAdapter(Protocol):
    version: str

    async def analyze(self, document_name: str) -> DocumentEvidence: ...


class LlmAdapter(Protocol):
    version: str

    async def invoke(
        self, stage: PromptStage, fixture_key: str = "default"
    ) -> dict[str, Any]: ...

