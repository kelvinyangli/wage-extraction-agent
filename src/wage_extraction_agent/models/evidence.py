"""Normalized evidence contracts at the external OCR/layout boundary."""

from __future__ import annotations

from pydantic import Field, NonNegativeInt, PositiveInt

from wage_extraction_agent.models.common import (
    Confidence,
    EvidenceLocation,
    StrictModel,
)


class EvidenceCell(StrictModel):
    row_index: NonNegativeInt
    column_index: NonNegativeInt
    text: str
    location: EvidenceLocation | None = None
    ocr_confidence: Confidence | None = None


class EvidenceTable(StrictModel):
    table_id: str = Field(min_length=1)
    cells: list[EvidenceCell] = Field(default_factory=list)


class EvidencePage(StrictModel):
    page_number: PositiveInt
    text: str
    tables: list[EvidenceTable] = Field(default_factory=list)
    ocr_confidence: Confidence | None = None


class DocumentEvidence(StrictModel):
    pages: list[EvidencePage] = Field(default_factory=list)
