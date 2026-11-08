import asyncio
import json
from pathlib import Path

import pytest

from wage_extraction_agent.adapters import (
    AdapterTimeoutError,
    FaultMode,
    FaultPlan,
    FixtureConfigurationError,
    FixtureRepository,
    MalformedAdapterResponseError,
    MockDocumentIntelligenceAdapter,
    MockLlmAdapter,
    PermanentAdapterError,
    PromptStage,
    TransientAdapterError,
)


FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "mock_services"


def run(coroutine):
    return asyncio.run(coroutine)


def repository() -> FixtureRepository:
    return FixtureRepository(FIXTURE_ROOT, "v1")


def test_repository_loads_explicit_mock_version():
    fixtures = repository()

    assert fixtures.version == "mock-services-v1"
    assert fixtures.manifest.mock_only is True


def test_document_adapter_returns_normalized_evidence():
    adapter = MockDocumentIntelligenceAdapter(repository())

    evidence = run(adapter.analyze("02-multipage-payslip.pdf"))

    assert adapter.version == "mock-di/mock-services-v1"
    assert [page.page_number for page in evidence.pages] == [1, 2]
    assert "Payslip 2 of 2" in evidence.pages[1].text


def test_document_fixture_missing_is_nonretryable():
    adapter = MockDocumentIntelligenceAdapter(repository())

    with pytest.raises(FixtureConfigurationError) as caught:
        run(adapter.analyze("missing.pdf"))

    assert caught.value.retryable is False


@pytest.mark.parametrize(
    ("mode", "error_type", "retryable"),
    [
        (FaultMode.TIMEOUT, AdapterTimeoutError, True),
        (FaultMode.TRANSIENT, TransientAdapterError, True),
        (FaultMode.PERMANENT, PermanentAdapterError, False),
    ],
)
def test_document_adapter_exposes_stable_failure_classification(
    mode, error_type, retryable
):
    call_key = "document_intelligence:01-two-employers.pdf"
    adapter = MockDocumentIntelligenceAdapter(
        repository(), FaultPlan({call_key: [mode]})
    )

    with pytest.raises(error_type) as caught:
        run(adapter.analyze("01-two-employers.pdf"))

    assert caught.value.retryable is retryable
    assert caught.value.call_key == call_key


def test_fault_sequence_is_consumed_then_adapter_recovers():
    call_key = "document_intelligence:01-two-employers.pdf"
    adapter = MockDocumentIntelligenceAdapter(
        repository(), FaultPlan({call_key: [FaultMode.TRANSIENT]})
    )

    with pytest.raises(TransientAdapterError):
        run(adapter.analyze("01-two-employers.pdf"))

    evidence = run(adapter.analyze("01-two-employers.pdf"))
    assert len(evidence.pages) == 2


def test_malformed_document_response_fails_at_adapter_boundary():
    call_key = "document_intelligence:03-pay-summary.pdf"
    adapter = MockDocumentIntelligenceAdapter(
        repository(), FaultPlan({call_key: [FaultMode.MALFORMED]})
    )

    with pytest.raises(MalformedAdapterResponseError) as caught:
        run(adapter.analyze("03-pay-summary.pdf"))

    assert caught.value.retryable is False


def test_llm_adapter_covers_all_approved_prompt_stages():
    adapter = MockLlmAdapter(repository())

    for stage in PromptStage:
        response = run(adapter.invoke(stage))
        assert isinstance(response, dict)
        assert response


def test_llm_fixture_responses_are_independent_copies():
    adapter = MockLlmAdapter(repository())

    first = run(adapter.invoke(PromptStage.LLM_AS_A_JUDGE))
    first["judge_outcome"] = "changed-by-test"
    second = run(adapter.invoke(PromptStage.LLM_AS_A_JUDGE))

    assert second["judge_outcome"] == "inconclusive"


def test_llm_malformed_fault_returns_raw_invalid_payload_for_node_validation():
    call_key = "llm:extract_payslip:default"
    adapter = MockLlmAdapter(
        repository(), FaultPlan({call_key: [FaultMode.MALFORMED]})
    )

    response = run(adapter.invoke(PromptStage.EXTRACT_PAYSLIP))

    assert response == {"__malformed_mock_response__": True}


def test_fixture_manifest_must_be_marked_mock_only(tmp_path):
    version = tmp_path / "v1"
    version.mkdir()
    (version / "manifest.json").write_text(
        json.dumps(
            {
                "fixture_version": "bad-v1",
                "schema_version": 1,
                "mock_only": False,
                "description": "Must be rejected.",
                "files": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FixtureConfigurationError):
        FixtureRepository(tmp_path, "v1")
