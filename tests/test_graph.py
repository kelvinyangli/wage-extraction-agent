import asyncio
import json
from pathlib import Path

import pytest

from wage_extraction_agent.adapters import (
    FaultMode,
    FaultPlan,
    FixtureRepository,
    MockLlmAdapter,
    PromptStage,
)
from wage_extraction_agent.models import (
    ComponentVersions,
    DocumentEvidence,
    DocumentState,
    ProcessingMetadata,
)
from wage_extraction_agent.models.enums import (
    AdapterMode,
    DocumentType,
    ProcessingStatus,
)
from wage_extraction_agent.workflow.graph import APPROVED_NODE_NAMES, build_graph
from wage_extraction_agent.workflow import publication


FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "mock_services"


def run(coroutine):
    return asyncio.run(coroutine)


def initial_state(*documents: DocumentState):
    return {
        "request_id": "request-graph-test",
        "claim_number": "CLAIM-001",
        "documents": list(documents),
        "status": ProcessingStatus.PARTIAL,
        "processing_metadata": ProcessingMetadata(),
        "adapter_mode": AdapterMode.MOCK,
        "max_concurrency": 2,
        "versions": ComponentVersions(
            model="mock-model-v1",
            prompt="prompt-v1",
            schema="schema-v1",
            mapping="mapping-v1",
            adapter="mock-adapter-v1",
            mock_fixture="mock-services-v1",
        ),
        "issues": [],
    }


def document(name: str, pages: int) -> DocumentState:
    return DocumentState(
        document_id=name.removesuffix(".pdf"),
        source_document_ref=name,
        page_count=pages,
        document_type=DocumentType.PAYSLIP,
        document_evidence=DocumentEvidence(),
        status=ProcessingStatus.PARTIAL,
    )


def test_graph_contains_exactly_the_twelve_approved_nodes(tmp_path):
    adapter = MockLlmAdapter(FixtureRepository(FIXTURE_ROOT, "v1"))
    graph = build_graph(llm_adapter=adapter, output_dir=tmp_path)

    actual = set(graph.get_graph().nodes) - {"__start__", "__end__"}

    assert actual == set(APPROVED_NODE_NAMES)


def test_graph_fans_out_two_payslips_and_publishes_api_projection(tmp_path):
    adapter = MockLlmAdapter(FixtureRepository(FIXTURE_ROOT, "v1"))
    graph = build_graph(llm_adapter=adapter, output_dir=tmp_path)

    result = run(graph.ainvoke(initial_state(document("01-two-employers.pdf", 2))))
    payload = json.loads(Path(result["output_path"]).read_text())

    assert result["publication_complete"] is True
    assert payload["processing_metadata"]["payslips"]["detected"] == 2
    assert len(payload["documents"][0]["payslips"]) == 2
    assert "document_evidence" not in payload["documents"][0]
    assert "source_document_ref" not in payload["documents"][0]


def test_graph_preserves_unresolved_section_without_stopping_other_payslips(tmp_path):
    adapter = MockLlmAdapter(FixtureRepository(FIXTURE_ROOT, "v1"))
    graph = build_graph(llm_adapter=adapter, output_dir=tmp_path)

    result = run(
        graph.ainvoke(initial_state(document("05-partial-and-unresolved.pdf", 3)))
    )
    payload = result["response_json"]

    assert payload["processing_metadata"]["payslips"]["detected"] == 2
    assert payload["processing_metadata"]["payslips"]["unresolved"] == 1
    assert payload["documents"][0]["status"] == "partial"


def test_invalid_extraction_uses_one_repair_then_returns_failed_record(tmp_path):
    call_key = "llm:extract_payslip:06-total-mismatch__pages_1"
    adapter = MockLlmAdapter(
        FixtureRepository(FIXTURE_ROOT, "v1"),
        FaultPlan({call_key: [FaultMode.MALFORMED]}),
    )
    graph = build_graph(llm_adapter=adapter, output_dir=tmp_path)

    result = run(graph.ainvoke(initial_state(document("06-total-mismatch.pdf", 1))))
    payslip = result["documents"][0].payslips[0]

    assert payslip.schema_repair_count == 1
    assert payslip.status is ProcessingStatus.FAILED
    assert payslip.validation_errors


def test_retryable_llm_failure_recovers_within_three_total_attempts(tmp_path):
    call_key = "llm:segment_documents:default"
    adapter = MockLlmAdapter(
        FixtureRepository(FIXTURE_ROOT, "v1"),
        FaultPlan({call_key: [FaultMode.TRANSIENT, FaultMode.TRANSIENT]}),
    )
    graph = build_graph(llm_adapter=adapter, output_dir=tmp_path)

    result = run(graph.ainvoke(initial_state(document("06-total-mismatch.pdf", 1))))

    assert result["publication_complete"] is True
    assert result["documents"][0].payslips


class ExtractionRetryAdapter:
    version = "scripted-extraction-retry-v1"

    def __init__(self):
        self.calls = []

    async def invoke(self, stage: PromptStage, fixture_key: str = "default"):
        self.calls.append(stage)
        if stage is PromptStage.SEGMENT_DOCUMENTS:
            return {
                "payslips": [
                    {
                        "signals": [],
                        "decision": "new_payslip",
                        "reason": "One payslip.",
                        "source_pages": [1],
                    }
                ],
                "unresolved_sections": [],
            }
        if stage is PromptStage.EXTRACT_PAYSLIP:
            return {
                "employer": {"name": "Example Employer", "abn": None, "fields": []},
                "employee": {"name": "Worker", "employee_id": None, "fields": []},
                "pay_period": {"start_date": None, "end_date": None, "payment_date": None, "frequency": None, "weeks_in_pay": None},
                "employment": {"base_rate": None, "base_hours": None},
                "currency": "AUD",
                "field_metadata": {},
                "line_items": [
                    {
                        "item_id": "mock-item-1",
                        "status": "complete",
                        "section": "Earnings",
                        "original_code": None,
                        "original_label": "Base Pay",
                        "group_label": "Gross",
                        "date": None,
                        "hours_or_units": None,
                        "rate": None,
                        "amount": "800.00",
                        "ytd_amount": None,
                        "currency": "AUD",
                        "source_page": 1,
                        "source_location": None,
                        "ocr_confidence": None,
                        "mapping_method": "rule",
                        "mapping_confidence": 1.0,
                        "issues": []
                    }
                ],
                "totals": [
                    {
                        "total_id": "gross-1",
                        "original_label": "Gross",
                        "total_type": "gross_pay",
                        "amount": "801.00",
                        "currency": "AUD",
                        "source_page": 1,
                        "issues": []
                    }
                ],
                "leave_balances": [],
                "other_fields": [],
                "reconciliation_checks": [],
                "validation_errors": [],
                "schema_repair_count": 0,
                "status": "successful",
                "issues": []
            }
        if stage is PromptStage.INTERPRET_TOTAL_RELATIONSHIPS:
            return {
                "terms": [
                    {"source_type":"pay_item","source_record_id": "mock-item-1", "multiplier": 1, "reason": "Gross contributor."}
                ],
                "explanation": "One gross item."
            }
        if stage is PromptStage.LLM_AS_A_JUDGE:
            return {
                "judge_outcome": "possible_extraction_error",
                "judge_reason": "The extracted source amount may be wrong.",
                "affected_field_paths": ["line_items.0.amount"]
            }
        if stage is PromptStage.RETRY_AFFECTED_EXTRACTION:
            return {
                "patch": {"line_items.0.amount": "801.00"},
                "affected_field_paths": ["line_items.0.amount"]
            }
        raise AssertionError(f"Unexpected stage: {stage}")


def test_judge_can_trigger_one_targeted_extraction_retry_then_match(tmp_path):
    adapter = ExtractionRetryAdapter()
    graph = build_graph(llm_adapter=adapter, output_dir=tmp_path)

    result = run(graph.ainvoke(initial_state(document("custom.pdf", 1))))
    check = result["documents"][0].payslips[0].reconciliation_checks[0]

    assert check.status.value == "matched"
    assert check.targeted_retry_count == 1
    assert check.targeted_retry_type.value == "extraction"
    assert adapter.calls.count(PromptStage.LLM_AS_A_JUDGE) == 1
    assert adapter.calls.count(PromptStage.RETRY_AFFECTED_EXTRACTION) == 1


class ItemSelectionRetryAdapter(ExtractionRetryAdapter):
    async def invoke(self, stage: PromptStage, fixture_key: str = "default"):
        if stage is PromptStage.LLM_AS_A_JUDGE:
            self.calls.append(stage)
            return {
                "judge_outcome": "possible_reconciliation_item_selection_error",
                "judge_reason": "The relationship may select the wrong items.",
                "affected_field_paths": [],
            }
        if stage is PromptStage.RETRY_RECONCILIATION_ITEM_SELECTION:
            self.calls.append(stage)
            return {
                "terms": [
                    {
                        "source_type":"pay_item","source_record_id": "mock-item-1",
                        "multiplier": 1,
                        "reason": "Retry still selects the supported gross item.",
                    }
                ],
                "explanation": "One bounded relationship retry.",
            }
        return await super().invoke(stage, fixture_key)


def test_judge_can_trigger_one_item_selection_retry_then_stop(tmp_path):
    adapter = ItemSelectionRetryAdapter()
    graph = build_graph(llm_adapter=adapter, output_dir=tmp_path)

    result = run(graph.ainvoke(initial_state(document("custom.pdf", 1))))
    check = result["documents"][0].payslips[0].reconciliation_checks[0]

    assert check.status.value == "mismatched"
    assert check.targeted_retry_count == 1
    assert check.targeted_retry_type.value == "reconciliation_item_selection"
    assert check.issues[0].review_required is True
    assert adapter.calls.count(PromptStage.LLM_AS_A_JUDGE) == 1
    assert adapter.calls.count(PromptStage.RETRY_RECONCILIATION_ITEM_SELECTION) == 1


def test_failed_atomic_replace_leaves_no_final_or_temporary_file(tmp_path, monkeypatch):
    adapter = MockLlmAdapter(FixtureRepository(FIXTURE_ROOT, "v1"))
    graph = build_graph(llm_adapter=adapter, output_dir=tmp_path)

    def fail_replace(source, destination):
        raise OSError("injected publication failure")

    monkeypatch.setattr(publication.os, "replace", fail_replace)

    with pytest.raises(OSError, match="injected publication failure"):
        run(graph.ainvoke(initial_state(document("01-two-employers.pdf", 2))))

    assert not (tmp_path / "request-graph-test.json").exists()
    assert list(tmp_path.glob("*.tmp")) == []
