import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from wage_extraction_agent.models import (
    BoundaryEvidence,
    ComponentVersions,
    DocumentEvidence,
    DocumentResult,
    DocumentState,
    ExtractionResponse,
    PayItem,
    PayslipState,
    PrintedTotal,
    ProcessingMetadata,
)
from wage_extraction_agent.models.enums import (
    AdapterMode,
    BoundaryDecision,
    DocumentType,
    GroupLabel,
    MappingMethod,
    PayItemStatus,
    ProcessingStatus,
    TotalType,
)


def make_boundary(*pages: int) -> BoundaryEvidence:
    return BoundaryEvidence(
        decision=BoundaryDecision.NEW_PAYSLIP,
        reason="First identified payslip",
        source_pages=list(pages),
    )


def make_payslip() -> PayslipState:
    return PayslipState(
        payslip_id="pay-1",
        document_id="doc-1",
        source_pages=[1],
        boundary_evidence=make_boundary(1),
        status=ProcessingStatus.SUCCESSFUL,
    )


def make_document(*, status=ProcessingStatus.SUCCESSFUL) -> DocumentState:
    return DocumentState(
        document_id="doc-1",
        source_document_ref="input/doc-1.pdf",
        page_count=1,
        document_type=DocumentType.PAYSLIP,
        document_evidence=DocumentEvidence(),
        payslips=[make_payslip()],
        status=status,
    )


def test_decimal_values_serialize_as_exact_strings():
    total = PrintedTotal(
        total_id="total-1",
        original_label="Net Pay",
        total_type=TotalType.NET_PAY,
        amount=Decimal("1892.30"),
        currency="AUD",
        source_page=1,
    )

    payload = json.loads(total.model_dump_json())

    assert payload["amount"] == "1892.30"


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        PrintedTotal(
            total_id="total-1",
            total_type=TotalType.UNKNOWN,
            source_page=1,
            invented_field="not allowed",
        )


def test_currency_requires_three_uppercase_letters():
    with pytest.raises(ValidationError):
        PrintedTotal(
            total_id="total-1",
            total_type=TotalType.NET_PAY,
            amount="1.00",
            currency="aud",
            source_page=1,
        )


@pytest.mark.parametrize("pages", ([2, 1], [1, 1]))
def test_source_pages_must_be_unique_and_ordered(pages):
    with pytest.raises(ValidationError):
        BoundaryEvidence(
            decision=BoundaryDecision.UNCERTAIN,
            reason="Ambiguous",
            source_pages=pages,
        )


def test_uncalibrated_llm_mapping_confidence_is_rejected():
    with pytest.raises(ValidationError):
        PayItem(
            item_id="item-1",
            status=PayItemStatus.COMPLETE,
            original_label="Special payment",
            group_label=GroupLabel.UNKNOWN,
            amount="12.00",
            currency="AUD",
            source_page=1,
            mapping_method=MappingMethod.LLM,
            mapping_confidence=0.9,
        )


def test_llm_mapping_without_numeric_confidence_is_valid():
    item = PayItem(
        item_id="item-1",
        status=PayItemStatus.COMPLETE,
        original_label="Special payment",
        group_label=GroupLabel.UNKNOWN,
        amount="12.00",
        currency="AUD",
        source_page=1,
        mapping_method=MappingMethod.LLM,
    )

    assert item.mapping_confidence is None


def test_schema_repair_count_is_bounded_to_one():
    with pytest.raises(ValidationError):
        PayslipState(
            payslip_id="pay-1",
            source_pages=[1],
            boundary_evidence=make_boundary(1),
            schema_repair_count=2,
            status=ProcessingStatus.PARTIAL,
        )


def test_response_uses_schema_alias_and_preserves_nulls_and_empty_lists():
    response = ExtractionResponse(
        request_id="req-1",
        claim_number=None,
        documents=[DocumentResult.from_state(make_document())],
        status=ProcessingStatus.SUCCESSFUL,
        processing_metadata=ProcessingMetadata(),
        adapter_mode=AdapterMode.MOCK,
        max_concurrency=2,
        versions=ComponentVersions(
            model="mock-model-v1",
            prompt="prompt-v1",
            schema="schema-v1",
            mapping="mapping-v1",
            adapter="mock-adapter-v1",
            mock_fixture="fixtures-v1",
        ),
    )

    payload = json.loads(response.model_dump_json(by_alias=True))

    assert payload["claim_number"] is None
    assert payload["versions"]["schema"] == "schema-v1"
    assert payload["issues"] == []
    assert "document_evidence" not in payload["documents"][0]
    assert "source_document_ref" not in payload["documents"][0]

